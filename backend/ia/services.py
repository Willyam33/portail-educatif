"""
Service d'accès à l'API Anthropic — questions libres et génération de contenu.

Ce service encapsule :
- le filtrage des questions sensibles avant tout appel externe,
- l'appel à Claude (Haiku pour les questions libres, Sonnet pour la génération),
- l'enregistrement de la consommation (jetons + coût estimé) dans ConsommationAPI,
- la persistance des entités générées (Lecon, QuestionQCM, Proposition, QuestionLibre).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import anthropic
from django.conf import settings
from django.db import transaction

from contenu.models import Lecon, Proposition, QuestionQCM, Thematique
from progression.models import QuestionLibre

from .filtres import contient_mot_clef_interdit
from .models import ConsommationAPI
from .prompts import (
    OUTIL_ENREGISTRER_QCM,
    REPONSE_PRE_ECRITE_SUJET_SENSIBLE,
    SYSTEM_PROMPT_LECON,
    SYSTEM_PROMPT_QCM,
    SYSTEM_PROMPT_QUESTION_LIBRE,
    USER_PROMPT_LECON,
    USER_PROMPT_QCM,
    USER_PROMPT_QUESTION_LIBRE,
    VERSION_PROMPT_LECON,
    VERSION_PROMPT_QCM,
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


class GenerationError(Exception):
    """Erreur métier levée lors de la génération d'une leçon ou d'un QCM."""


@dataclass
class ReponseIA:
    """Valeur retournée par le service après un appel réussi (ou pré-filtré)."""

    reponse: str
    jetons_entree: int
    jetons_sortie: int
    filtree: bool  # True si interceptée par le filtre (pas d'appel API effectué)
    question_libre: QuestionLibre


@dataclass
class ResultatGeneration:
    """Valeur retournée après la génération d'une leçon ou d'un QCM."""

    jetons_entree: int
    jetons_sortie: int
    cout_eur: Decimal
    # Une des deux valeurs est renseignée selon le type d'appel :
    lecon: Lecon | None = None
    questions: list[QuestionQCM] | None = None


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
    """Client applicatif autour du SDK Anthropic."""

    def __init__(self) -> None:
        # Client instancié à la demande : on ne bloque pas si la clé est absente
        # tant que le filtre local n'a pas eu sa chance.
        self._client = None
        self._modele = settings.ANTHROPIC_MODEL_QUESTIONS_LIBRES
        self._modele_generation = settings.ANTHROPIC_MODEL_GENERATION

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

    # ------------------------------------------------------------------
    # Génération de contenu (leçons + QCM)
    # ------------------------------------------------------------------

    def _appel_generation(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        """Appel brut à Claude Sonnet pour la génération ; retourne (texte, in, out)."""
        client = self._client_anthropic()
        try:
            message = client.messages.create(
                model=self._modele_generation,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIConnectionError as exc:
            raise GenerationError("Impossible de joindre Claude pour le moment.") from exc
        except anthropic.RateLimitError as exc:
            raise GenerationError("Claude est surchargé, réessaie dans un instant.") from exc
        except anthropic.APIError as exc:
            raise GenerationError(f"Erreur côté Claude : {exc}") from exc

        texte = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
        if not texte:
            raise GenerationError("Réponse vide reçue de Claude.")
        return (
            texte,
            int(message.usage.input_tokens or 0),
            int(message.usage.output_tokens or 0),
        )

    def generer_lecon(self, thematique: Thematique) -> ResultatGeneration:
        """Génère la leçon Markdown d'une thématique via Claude Sonnet 4.6."""
        chapitre_titre = thematique.chapitre.titre if thematique.chapitre else "(non précisé)"
        user_prompt = USER_PROMPT_LECON.format(
            matiere=thematique.matiere.nom,
            titre_thematique=thematique.titre,
            chapitre_programme=chapitre_titre,
            difficulte=thematique.difficulte,
            objectifs=thematique.objectifs_apprentissage or "(non précisés)",
            notions=thematique.notions or "(non précisées)",
            prerequis=thematique.prerequis or "(aucun)",
        )
        texte, jetons_in, jetons_out = self._appel_generation(
            system_prompt=SYSTEM_PROMPT_LECON,
            user_prompt=user_prompt,
            max_tokens=4000,
            temperature=0.5,
        )
        cout = _cout_estime_eur(self._modele_generation, jetons_in, jetons_out)

        with transaction.atomic():
            lecon, _ = Lecon.objects.update_or_create(
                thematique=thematique,
                defaults={
                    "contenu": texte,
                    "mots_cles": thematique.mots_cles or [],
                    "modele_ia_utilise": self._modele_generation,
                    "version_prompt": VERSION_PROMPT_LECON,
                },
            )
            if thematique.statut == Thematique.Statut.PLANIFIEE:
                thematique.statut = Thematique.Statut.GENEREE
                thematique.save(update_fields=["statut"])
            ConsommationAPI.objects.create(
                type_appel=ConsommationAPI.TypeAppel.GENERATION_LECON,
                modele=self._modele_generation,
                jetons_entree=jetons_in,
                jetons_sortie=jetons_out,
                cout_estime_euros=cout,
            )

        return ResultatGeneration(
            jetons_entree=jetons_in,
            jetons_sortie=jetons_out,
            cout_eur=cout,
            lecon=lecon,
        )

    def generer_qcm(self, thematique: Thematique) -> ResultatGeneration:
        """Génère le QCM d'une thématique à partir de sa leçon déjà produite.

        Utilise un tool forcé côté Anthropic pour garantir un JSON valide : Claude
        renvoie ses questions en appelant l'outil `enregistrer_qcm`, et le SDK
        valide automatiquement le JSON contre le schéma défini.
        """
        lecon = getattr(thematique, "lecon", None)
        if lecon is None or not lecon.contenu.strip():
            raise GenerationError(
                "La leçon est absente : impossible de générer le QCM. "
                "Lance d'abord `generer_lecon`."
            )

        user_prompt = USER_PROMPT_QCM.format(
            matiere=thematique.matiere.nom,
            titre_thematique=thematique.titre,
            difficulte=thematique.difficulte,
            contenu_lecon=lecon.contenu,
        )

        client = self._client_anthropic()
        try:
            message = client.messages.create(
                model=self._modele_generation,
                max_tokens=8000,
                temperature=0.3,
                system=SYSTEM_PROMPT_QCM,
                tools=[OUTIL_ENREGISTRER_QCM],
                tool_choice={"type": "tool", "name": "enregistrer_qcm"},
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIConnectionError as exc:
            raise GenerationError("Impossible de joindre Claude pour le moment.") from exc
        except anthropic.RateLimitError as exc:
            raise GenerationError("Claude est surchargé, réessaie dans un instant.") from exc
        except anthropic.APIError as exc:
            raise GenerationError(f"Erreur côté Claude : {exc}") from exc

        jetons_in = int(message.usage.input_tokens or 0)
        jetons_out = int(message.usage.output_tokens or 0)
        cout = _cout_estime_eur(self._modele_generation, jetons_in, jetons_out)

        if message.stop_reason == "max_tokens":
            raise GenerationError(
                "La réponse a été tronquée (max_tokens atteint) : le QCM est incomplet. "
                "Augmente max_tokens ou réduis le contenu de la leçon."
            )

        tool_use = next(
            (b for b in message.content if getattr(b, "type", None) == "tool_use"),
            None,
        )
        if tool_use is None:
            raise GenerationError(
                "Claude n'a pas appelé l'outil `enregistrer_qcm` (aucun tool_use dans la réponse)."
            )
        questions_brutes = (tool_use.input or {}).get("questions") or []
        if not questions_brutes:
            raise GenerationError("Le QCM généré ne contient aucune question.")

        with transaction.atomic():
            # Remplacement atomique : on supprime les anciennes questions et propositions.
            thematique.questions.all().delete()
            questions_creees: list[QuestionQCM] = []
            for q in questions_brutes:
                propositions = q.get("propositions") or []
                if len(propositions) < 2:
                    raise GenerationError(
                        f"Question {q.get('ordre')} : moins de 2 propositions."
                    )
                nb_correctes = sum(1 for p in propositions if p.get("est_correcte"))
                if nb_correctes != 1:
                    raise GenerationError(
                        f"Question {q.get('ordre')} : {nb_correctes} réponses correctes (attendu 1)."
                    )
                question = QuestionQCM.objects.create(
                    thematique=thematique,
                    enonce=q["enonce"],
                    difficulte=int(q.get("difficulte") or thematique.difficulte),
                    ordre=int(q.get("ordre") or (len(questions_creees) + 1)),
                    explication_generale=q.get("explication_generale", ""),
                )
                for prop in propositions:
                    Proposition.objects.create(
                        question=question,
                        texte=prop["texte"],
                        est_correcte=bool(prop.get("est_correcte")),
                        explication=prop.get("explication", ""),
                        ordre=int(prop.get("ordre") or 0),
                    )
                questions_creees.append(question)

            if thematique.statut == Thematique.Statut.PLANIFIEE:
                thematique.statut = Thematique.Statut.GENEREE
                thematique.save(update_fields=["statut"])
            ConsommationAPI.objects.create(
                type_appel=ConsommationAPI.TypeAppel.GENERATION_QCM,
                modele=self._modele_generation,
                jetons_entree=jetons_in,
                jetons_sortie=jetons_out,
                cout_estime_euros=cout,
            )

        return ResultatGeneration(
            jetons_entree=jetons_in,
            jetons_sortie=jetons_out,
            cout_eur=cout,
            questions=questions_creees,
        )


