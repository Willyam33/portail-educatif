"""
Service d'accès à l'API Anthropic — questions libres de l'élève (voir specs §6).

Ce service encapsule :
- le filtrage des questions sensibles avant tout appel externe,
- l'appel à Claude Haiku 4.5 avec les bons paramètres (max_tokens=800, temperature=0.6),
- l'enregistrement de la consommation (jetons + coût estimé) dans ConsommationAPI,
- la création de l'entrée QuestionLibre en base.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import anthropic
from django.conf import settings

from contenu.models import Thematique
from progression.models import QuestionLibre

from .filtres import contient_mot_clef_interdit
from .models import ConsommationAPI
from .prompts import (
    REPONSE_PRE_ECRITE_SUJET_SENSIBLE,
    SYSTEM_PROMPT_QUESTION_LIBRE,
    USER_PROMPT_QUESTION_LIBRE,
)


# Tarifs Claude Haiku 4.5 (USD par million de jetons). On les garde ici pour estimer
# grossièrement le coût ; si les tarifs bougent, on met à jour le dictionnaire.
TARIFS_USD_PAR_MILLION = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
}
TAUX_USD_VERS_EUR = Decimal("0.92")

# Nombre de caractères du contenu de leçon envoyé en contexte.
# On reste modeste pour limiter les jetons d'entrée (l'élève a déjà la leçon sous les yeux).
LONGUEUR_MAX_RESUME_LECON = 2000


class QuestionLibreError(Exception):
    """Erreur métier levée lorsqu'on ne peut pas répondre à la question."""


@dataclass
class ReponseIA:
    """Valeur retournée par le service après un appel réussi (ou pré-filtré)."""

    reponse: str
    jetons_entree: int
    jetons_sortie: int
    filtree: bool  # True si interceptée par le filtre (pas d'appel API effectué)
    question_libre: QuestionLibre


def _cout_estime_eur(modele: str, jetons_entree: int, jetons_sortie: int) -> Decimal:
    tarifs = TARIFS_USD_PAR_MILLION.get(modele)
    if not tarifs:
        return Decimal("0")
    cout_usd = Decimal(jetons_entree) * Decimal(str(tarifs["input"])) / Decimal(1_000_000)
    cout_usd += Decimal(jetons_sortie) * Decimal(str(tarifs["output"])) / Decimal(1_000_000)
    cout_eur = cout_usd * TAUX_USD_VERS_EUR
    return cout_eur.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _resume_lecon(thematique: Thematique) -> str:
    """Extrait un contexte court de la leçon pour alimenter le prompt utilisateur."""
    lecon = getattr(thematique, "lecon", None)
    if not lecon or not lecon.contenu:
        return "(pas de leçon disponible)"
    contenu = lecon.contenu.strip()
    if len(contenu) <= LONGUEUR_MAX_RESUME_LECON:
        return contenu
    return contenu[:LONGUEUR_MAX_RESUME_LECON] + "…"


class ServiceClaude:
    """Client applicatif autour du SDK Anthropic pour les questions libres."""

    def __init__(self) -> None:
        # Client instancié à la demande : on ne bloque pas si la clé est absente
        # tant que le filtre local n'a pas eu sa chance.
        self._client = None
        self._modele = settings.ANTHROPIC_MODEL_QUESTIONS_LIBRES

    def _client_anthropic(self):
        if self._client is not None:
            return self._client
        if not settings.ANTHROPIC_API_KEY:
            raise QuestionLibreError(
                "Clé API Anthropic absente : impossible d'appeler Claude."
            )
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def repondre_question_libre(
        self, *, question: str, thematique: Thematique, eleve,
    ) -> ReponseIA:
        question_nettoyee = (question or "").strip()
        if not question_nettoyee:
            raise QuestionLibreError("La question est vide.")

        # 1. Filtrage garde-fous (aucun appel API si mot-clé interdit).
        if contient_mot_clef_interdit(question_nettoyee):
            question_libre = QuestionLibre.objects.create(
                eleve=eleve,
                thematique=thematique,
                question=question_nettoyee,
                reponse=REPONSE_PRE_ECRITE_SUJET_SENSIBLE,
                jetons_entree=0,
                jetons_sortie=0,
            )
            return ReponseIA(
                reponse=REPONSE_PRE_ECRITE_SUJET_SENSIBLE,
                jetons_entree=0,
                jetons_sortie=0,
                filtree=True,
                question_libre=question_libre,
            )

        # 2. Appel à Claude.
        client = self._client_anthropic()
        user_prompt = USER_PROMPT_QUESTION_LIBRE.format(
            matiere=thematique.matiere.nom,
            titre_thematique=thematique.titre,
            contenu_lecon_resume=_resume_lecon(thematique),
            question_eleve=question_nettoyee,
        )
        try:
            message = client.messages.create(
                model=self._modele,
                max_tokens=800,
                temperature=0.6,
                system=SYSTEM_PROMPT_QUESTION_LIBRE,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIConnectionError as exc:
            raise QuestionLibreError(
                "Impossible de joindre Claude pour le moment."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise QuestionLibreError(
                "Claude est surchargé, réessaie dans un instant."
            ) from exc
        except anthropic.APIError as exc:
            raise QuestionLibreError(
                "Une erreur est survenue côté Claude."
            ) from exc

        texte = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
        if not texte:
            raise QuestionLibreError("Réponse vide reçue de Claude.")

        jetons_entree = int(message.usage.input_tokens or 0)
        jetons_sortie = int(message.usage.output_tokens or 0)

        # 3. Enregistrement consommation + question libre (en base).
        ConsommationAPI.objects.create(
            utilisateur=eleve,
            type_appel=ConsommationAPI.TypeAppel.QUESTION_LIBRE,
            modele=self._modele,
            jetons_entree=jetons_entree,
            jetons_sortie=jetons_sortie,
            cout_estime_euros=_cout_estime_eur(self._modele, jetons_entree, jetons_sortie),
        )
        question_libre = QuestionLibre.objects.create(
            eleve=eleve,
            thematique=thematique,
            question=question_nettoyee,
            reponse=texte,
            jetons_entree=jetons_entree,
            jetons_sortie=jetons_sortie,
        )
        return ReponseIA(
            reponse=texte,
            jetons_entree=jetons_entree,
            jetons_sortie=jetons_sortie,
            filtree=False,
            question_libre=question_libre,
        )
