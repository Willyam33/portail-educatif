"""
Helpers partagés par les commandes `generer_lecon` et `generer_qcm`.

Sélection de thématiques cibles + formatage de la sortie console, pour éviter
de dupliquer la logique entre les deux commandes.
"""

from __future__ import annotations

from django.core.management.base import CommandError
from django.db.models import QuerySet

from contenu.models import Matiere, Thematique


def ajouter_arguments_selection(parser) -> None:
    """Ajoute les arguments communs de ciblage à un parser argparse."""
    parser.add_argument(
        "--thematique",
        type=int,
        help="Cible une seule thématique par son ID.",
    )
    parser.add_argument(
        "--jour",
        type=int,
        help="Cible la thématique du jour global N (1 à 180).",
    )
    parser.add_argument(
        "--jours",
        type=str,
        help="Plage de jours globaux au format N-M (ex. 10-20, bornes incluses).",
    )
    parser.add_argument(
        "--matiere",
        type=str,
        help="Code matière (FR, MATH, HIST, GEO, PC, SVT, TECH) ou 'all'.",
    )
    parser.add_argument(
        "--nb",
        type=int,
        default=None,
        help="Limite le nombre de thématiques traitées (ordre : matière puis numéro).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Régénère même si la leçon/QCM existe déjà.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Liste les thématiques cibles sans appeler Claude.",
    )


def resoudre_thematiques(options: dict) -> QuerySet[Thematique]:
    """Retourne un queryset de thématiques selon les filtres fournis."""
    qs = Thematique.objects.select_related("matiere", "chapitre").order_by(
        "matiere__ordre", "numero_dans_matiere"
    )

    filtres_exclusifs = [
        bool(options.get("thematique")),
        bool(options.get("jour")),
        bool(options.get("jours")),
    ]
    if sum(filtres_exclusifs) > 1:
        raise CommandError(
            "Les options --thematique, --jour et --jours sont mutuellement exclusives."
        )

    if options.get("thematique"):
        qs = qs.filter(pk=options["thematique"])
    elif options.get("jour"):
        qs = qs.filter(numero_jour=options["jour"])
    elif options.get("jours"):
        debut, fin = _parser_plage_jours(options["jours"])
        qs = qs.filter(numero_jour__gte=debut, numero_jour__lte=fin)

    matiere_code = (options.get("matiere") or "").strip()
    if matiere_code and matiere_code.lower() != "all":
        if not Matiere.objects.filter(code__iexact=matiere_code).exists():
            raise CommandError(f"Matière inconnue : {matiere_code}")
        qs = qs.filter(matiere__code__iexact=matiere_code)

    if options.get("nb"):
        qs = qs[: options["nb"]]

    return qs


def _parser_plage_jours(valeur: str) -> tuple[int, int]:
    try:
        debut_s, fin_s = valeur.split("-", 1)
        debut, fin = int(debut_s), int(fin_s)
    except ValueError as exc:
        raise CommandError("Format attendu pour --jours : N-M (ex. 10-20).") from exc
    if debut > fin:
        raise CommandError("--jours : le début doit être inférieur ou égal à la fin.")
    return debut, fin


def libelle_thematique(thematique: Thematique) -> str:
    jour = f"J{thematique.numero_jour}" if thematique.numero_jour else "J?"
    return f"{jour} {thematique.matiere.code}#{thematique.numero_dans_matiere} — {thematique.titre}"
