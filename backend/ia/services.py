"""
Service d'accès à Claude via le SDK Claude Code — utilise l'abonnement Claude Max.

Les appels passent par `claude-agent-sdk`, qui pilote le CLI Claude Code en mode
non-interactif. L'authentification est celle du CLI Claude Code (OAuth
abonnement), donc les appels consomment le quota de l'abonnement Max 5x et ne
sont pas facturés sur le compte API Anthropic.

Différences par rapport à l'API Anthropic directe :
- Pas de `tool_use` forcé : le QCM est demandé en JSON strict dans le prompt et
  parsé côté Python (robuste car le SDK tolère les fences markdown).
- ~2x plus lent (~30s par appel) à cause du démarrage du sous-processus Claude.
- Coût facturé nul (abonnement), mais consommation de quota à surveiller.
- Métriques conservées (jetons in/out) pour le suivi ; `cout_estime_euros` est
  figé à 0 puisque l'abonnement couvre les appels.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from decimal import Decimal

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from django.conf import settings
from django.db import transaction

from contenu.models import Lecon, Proposition, QuestionQCM, Thematique
from progression.models import QuestionLibre

from .filtres import contient_mot_clef_interdit
from .models import ConsommationAPI
from .prompts import (
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


# Longueur du résumé de leçon envoyé en contexte d'une question libre : on reste
# modeste pour limiter les jetons (l'élève a déjà la leçon sous les yeux).
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
    filtree: bool  # True si interceptée par le filtre (pas d'appel SDK effectué)
    question_libre: QuestionLibre


@dataclass
class ResultatGeneration:
    """Valeur retournée après la génération d'une leçon ou d'un QCM."""

    jetons_entree: int
    jetons_sortie: int
    cout_eur: Decimal  # Toujours 0 via abonnement ; conservé pour compat API.
    lecon: Lecon | None = None
    questions: list[QuestionQCM] | None = None


def _resume_lecon(thematique: Thematique) -> str:
    """Extrait un contexte court de la leçon pour alimenter un prompt utilisateur."""
    lecon = getattr(thematique, "lecon", None)
    if not lecon or not lecon.contenu:
        return "(pas de leçon disponible)"
    contenu = lecon.contenu.strip()
    if len(contenu) <= LONGUEUR_MAX_RESUME_LECON:
        return contenu
    return contenu[:LONGUEUR_MAX_RESUME_LECON] + "…"


def _extraire_json(texte: str) -> dict:
    """Extrait un objet JSON d'une réponse texte (tolère les fences markdown)."""
    texte = texte.strip()
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texte, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut >= 0 and fin > debut:
        return json.loads(texte[debut : fin + 1])
    raise ValueError("Aucun objet JSON valide trouvé dans la réponse.")


async def _appel_claude_async(
    system_prompt: str, user_prompt: str, modele: str
) -> tuple[str, int, int]:
    """Lance un appel unique via claude-agent-sdk et retourne (texte, in, out)."""
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=[],
        max_turns=1,
        model=modele,
    )

    morceaux_texte: list[str] = []
    jetons_in = 0
    jetons_out = 0

    async for msg in query(prompt=user_prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    morceaux_texte.append(block.text)
        elif isinstance(msg, ResultMessage):
            usage = msg.usage or {}
            jetons_in = int(usage.get("input_tokens", 0) or 0)
            jetons_out = int(usage.get("output_tokens", 0) or 0)

    texte = "".join(morceaux_texte).strip()
    if not texte:
        raise GenerationError("Réponse vide reçue de Claude.")
    return texte, jetons_in, jetons_out


def _appel_claude(
    system_prompt: str, user_prompt: str, modele: str
) -> tuple[str, int, int]:
    """Adaptateur sync pour `_appel_claude_async` (utilisé depuis code Django sync)."""
    try:
        return anyio.run(
            functools.partial(_appel_claude_async, system_prompt, user_prompt, modele)
        )
    except Exception as exc:  # noqa: BLE001
        raise GenerationError(f"Erreur côté Claude (SDK) : {exc}") from exc


class ServiceClaude:
    """Client applicatif utilisant claude-agent-sdk + l'abonnement Claude Max."""

    def __init__(self) -> None:
        # Les noms de modèles restent dans les settings pour traçabilité dans
        # `ConsommationAPI`, même si le SDK utilise le modèle actif de Claude Code.
        self._modele_questions = settings.ANTHROPIC_MODEL_QUESTIONS_LIBRES
        self._modele_generation = settings.ANTHROPIC_MODEL_GENERATION

    def repondre_question_libre(
        self, *, question: str, thematique: Thematique, eleve,
    ) -> ReponseIA:
        question_nettoyee = (question or "").strip()
        if not question_nettoyee:
            raise QuestionLibreError("La question est vide.")

        # 1. Filtrage garde-fous : aucun appel si mot-clé interdit détecté.
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

        # 2. Appel à Claude via le SDK (abonnement Max).
        user_prompt = USER_PROMPT_QUESTION_LIBRE.format(
            matiere=thematique.matiere.nom,
            titre_thematique=thematique.titre,
            contenu_lecon_resume=_resume_lecon(thematique),
            question_eleve=question_nettoyee,
        )
        try:
            texte, jetons_in, jetons_out = _appel_claude(
                SYSTEM_PROMPT_QUESTION_LIBRE, user_prompt, self._modele_questions
            )
        except GenerationError as exc:
            raise QuestionLibreError(str(exc)) from exc

        # 3. Enregistrement consommation + question libre (coût 0 via abonnement).
        ConsommationAPI.objects.create(
            utilisateur=eleve,
            type_appel=ConsommationAPI.TypeAppel.QUESTION_LIBRE,
            modele=self._modele_questions,
            jetons_entree=jetons_in,
            jetons_sortie=jetons_out,
            cout_estime_euros=Decimal("0"),
        )
        question_libre = QuestionLibre.objects.create(
            eleve=eleve,
            thematique=thematique,
            question=question_nettoyee,
            reponse=texte,
            jetons_entree=jetons_in,
            jetons_sortie=jetons_out,
        )
        return ReponseIA(
            reponse=texte,
            jetons_entree=jetons_in,
            jetons_sortie=jetons_out,
            filtree=False,
            question_libre=question_libre,
        )

    # ------------------------------------------------------------------
    # Génération de contenu (leçons + QCM)
    # ------------------------------------------------------------------

    def generer_lecon(self, thematique: Thematique) -> ResultatGeneration:
        """Génère la leçon Markdown d'une thématique via le SDK."""
        chapitre_titre = (
            thematique.chapitre.titre if thematique.chapitre else "(non précisé)"
        )
        user_prompt = USER_PROMPT_LECON.format(
            matiere=thematique.matiere.nom,
            titre_thematique=thematique.titre,
            chapitre_programme=chapitre_titre,
            difficulte=thematique.difficulte,
            objectifs=thematique.objectifs_apprentissage or "(non précisés)",
            notions=thematique.notions or "(non précisées)",
            prerequis=thematique.prerequis or "(aucun)",
        )
        texte, jetons_in, jetons_out = _appel_claude(
            SYSTEM_PROMPT_LECON, user_prompt, self._modele_generation
        )
        cout = Decimal("0")

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

        Demande un JSON strict dans la réponse (le SDK Claude Code ne supporte
        pas le `tool_use` forcé). La réponse est parsée côté Python avec une
        tolérance pour les fences markdown éventuelles.
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

        texte, jetons_in, jetons_out = _appel_claude(
            SYSTEM_PROMPT_QCM, user_prompt, self._modele_generation
        )

        try:
            donnees = _extraire_json(texte)
        except (ValueError, json.JSONDecodeError) as exc:
            raise GenerationError(
                f"Le JSON du QCM est invalide : {exc}. "
                f"Début de la réponse : {texte[:200]}…"
            ) from exc

        questions_brutes = donnees.get("questions") or []
        if not questions_brutes:
            raise GenerationError("Le QCM généré ne contient aucune question.")

        cout = Decimal("0")

        with transaction.atomic():
            # Remplacement atomique : on supprime d'abord les anciennes questions.
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
                        f"Question {q.get('ordre')} : {nb_correctes} réponses "
                        f"correctes (attendu 1)."
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
