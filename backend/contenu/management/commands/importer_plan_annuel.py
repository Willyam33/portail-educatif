"""
Commande d'import des plans annuels depuis docs/plans_annuels/*.md.

Exemple d'utilisation :

    python manage.py importer_plan_annuel
    python manage.py importer_plan_annuel --matiere mathematiques
    python manage.py importer_plan_annuel --dossier chemin/vers/plans

Pour chaque fichier plan_annuel_<matiere>.md, le parseur extrait chaque bloc
`#### Thématique N` et crée (ou met à jour) la Matiere, les ChapitreProgramme
référencés et les Thematique associées.

Le champ `numero_jour` (position dans le calendrier des 180 jours) n'est pas
renseigné à l'import : il sera attribué par une commande d'ordonnancement
ultérieure, ou à la main dans l'admin.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contenu.models import ChapitreProgramme, Matiere, Thematique


# --- Configuration des matières ---------------------------------------------

# Association entre le nom figurant dans le nom de fichier et les métadonnées
# à enregistrer en base. Les couleurs suivent une palette Tailwind (lisible).
MATIERES_CONFIG = {
    "francais": {
        "code": "FR",
        "nom": "Français",
        "couleur": "#2563eb",
        "ordre": 1,
    },
    "mathematiques": {
        "code": "MATH",
        "nom": "Mathématiques",
        "couleur": "#ea580c",
        "ordre": 2,
    },
    "physique_chimie": {
        "code": "PC",
        "nom": "Physique-Chimie",
        "couleur": "#7c3aed",
        "ordre": 3,
    },
    "svt": {
        "code": "SVT",
        "nom": "Sciences de la Vie et de la Terre",
        "couleur": "#16a34a",
        "ordre": 4,
    },
    "histoire": {
        "code": "HIST",
        "nom": "Histoire",
        "couleur": "#b45309",
        "ordre": 5,
    },
    "geographie": {
        "code": "GEO",
        "nom": "Géographie",
        "couleur": "#0891b2",
        "ordre": 6,
    },
    "technologie": {
        "code": "TECH",
        "nom": "Technologie",
        "couleur": "#64748b",
        "ordre": 7,
    },
}


# --- Parseur Markdown -------------------------------------------------------

RE_FILE_MATIERE = re.compile(r"plan_annuel_([a-z_]+)\.md$")
RE_THEMATIQUE = re.compile(r"^####\s+Thématique\s+(\d+)\s*$")
RE_CHAMP = re.compile(r"^\s*-\s+\*\*(?P<label>[^*]+)\*\*\s*:\s*(?P<valeur>.*)$")
RE_SOUS_PUCE = re.compile(r"^\s{2,}-\s+(.*)$")
RE_FIN_BLOC = re.compile(r"^(---|##\s|###\s|####\s|\Z)")


@dataclass
class ThematiqueParsee:
    """Représentation intermédiaire d'une thématique avant persistance."""

    numero: int
    champs: dict[str, str | list[str]] = field(default_factory=dict)

    def titre(self) -> str:
        return str(self.champs.get("Titre", "")).strip()

    def chapitre(self) -> str:
        # L'étiquette varie selon les plans : "Chapitre du programme", "Domaine", "Thème".
        for cle in ("Chapitre du programme", "Domaine", "Thème"):
            valeur = self.champs.get(cle)
            if valeur:
                return str(valeur).strip()
        return ""

    def objectifs(self) -> str:
        valeur = self.champs.get("Objectifs pédagogiques", "")
        if isinstance(valeur, list):
            return "\n".join(f"- {item}" for item in valeur)
        return str(valeur).strip()

    def notions(self) -> str:
        return str(self.champs.get("Notions", "")).strip()

    def prerequis(self) -> str:
        return str(self.champs.get("Pré-requis", "")).strip()

    def difficulte(self) -> int:
        brut = str(self.champs.get("Difficulté", "2")).strip()
        try:
            return max(1, min(3, int(brut)))
        except ValueError:
            return 2

    def mots_cles(self) -> list[str]:
        brut = self.champs.get("Mots-clés", "")
        if not brut:
            return []
        return [m.strip() for m in str(brut).split(",") if m.strip()]


def parser_fichier(chemin: Path) -> list[ThematiqueParsee]:
    """Parse un fichier plan_annuel_*.md et retourne la liste des thématiques."""

    lignes = chemin.read_text(encoding="utf-8").splitlines()
    thematiques: list[ThematiqueParsee] = []
    courante: ThematiqueParsee | None = None
    champ_multi: str | None = None

    for ligne in lignes:
        match_them = RE_THEMATIQUE.match(ligne)
        if match_them:
            if courante is not None:
                thematiques.append(courante)
            courante = ThematiqueParsee(numero=int(match_them.group(1)))
            champ_multi = None
            continue

        if courante is None:
            continue

        match_champ = RE_CHAMP.match(ligne)
        if match_champ:
            label = match_champ.group("label").strip()
            valeur = match_champ.group("valeur").strip()
            if valeur:
                courante.champs[label] = valeur
                champ_multi = None
            else:
                # Champ multi-ligne (sous-puces qui suivent).
                courante.champs[label] = []
                champ_multi = label
            continue

        match_sous = RE_SOUS_PUCE.match(ligne)
        if match_sous and champ_multi is not None:
            liste = courante.champs.setdefault(champ_multi, [])
            if isinstance(liste, list):
                liste.append(match_sous.group(1).strip())
            continue

        if ligne.strip() == "" or ligne.startswith("#"):
            champ_multi = None
            # Si on atteint une nouvelle section/titre sans thématique nouvelle,
            # on ferme le bloc courant uniquement sur ---.
            if ligne.startswith("---"):
                thematiques.append(courante)
                courante = None

    if courante is not None:
        thematiques.append(courante)

    return thematiques


# --- Commande Django --------------------------------------------------------


class Command(BaseCommand):
    help = "Importe les plans annuels depuis docs/plans_annuels/*.md dans la base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dossier",
            type=str,
            default=None,
            help="Dossier contenant les fichiers plan_annuel_*.md. Par défaut : docs/plans_annuels/ du dépôt.",
        )
        parser.add_argument(
            "--matiere",
            type=str,
            default=None,
            help="Slug de la matière à importer (ex. mathematiques). Par défaut : toutes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="N'écrit rien en base, affiche seulement ce qui serait fait.",
        )

    def handle(self, *args, **options):
        dossier = Path(
            options["dossier"]
            or Path(__file__).resolve().parents[4] / "docs" / "plans_annuels"
        )
        if not dossier.is_dir():
            raise CommandError(f"Dossier introuvable : {dossier}")

        filtre_matiere = options.get("matiere")
        dry_run = options.get("dry_run", False)

        fichiers = sorted(dossier.glob("plan_annuel_*.md"))
        if not fichiers:
            raise CommandError(f"Aucun fichier plan_annuel_*.md trouvé dans {dossier}")

        total_themes = 0
        for fichier in fichiers:
            match = RE_FILE_MATIERE.search(fichier.name)
            if not match:
                self.stderr.write(f"Nom inattendu, ignoré : {fichier.name}")
                continue
            slug = match.group(1)
            config = MATIERES_CONFIG.get(slug)
            if config is None:
                self.stderr.write(f"Matière inconnue, ignoré : {slug}")
                continue
            if filtre_matiere and slug != filtre_matiere:
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f"== {config['nom']} ({fichier.name})"))
            themes = parser_fichier(fichier)
            self.stdout.write(f"  {len(themes)} thématique(s) détectée(s).")

            if not dry_run:
                with transaction.atomic():
                    total_themes += self._importer(config, themes)
            else:
                for t in themes:
                    self.stdout.write(f"  - #{t.numero:>2} {t.titre()}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {total_themes} thématique(s) enregistrée(s)."
                if not dry_run
                else "Mode --dry-run : aucune écriture."
            )
        )

    def _importer(self, config: dict, themes: list[ThematiqueParsee]) -> int:
        matiere, _ = Matiere.objects.update_or_create(
            code=config["code"],
            defaults={
                "nom": config["nom"],
                "couleur": config["couleur"],
                "ordre": config["ordre"],
            },
        )

        # On construit un dictionnaire chapitre → instance (créé à la volée).
        chapitres: dict[str, ChapitreProgramme] = {}

        compte = 0
        for theme in themes:
            titre_chapitre = theme.chapitre()
            chapitre = None
            if titre_chapitre:
                chapitre = chapitres.get(titre_chapitre)
                if chapitre is None:
                    chapitre, _ = ChapitreProgramme.objects.get_or_create(
                        matiere=matiere,
                        titre=titre_chapitre,
                    )
                    chapitres[titre_chapitre] = chapitre

            Thematique.objects.update_or_create(
                matiere=matiere,
                numero_dans_matiere=theme.numero,
                defaults={
                    "titre": theme.titre() or f"Thématique {theme.numero}",
                    "chapitre": chapitre,
                    "objectifs_apprentissage": theme.objectifs(),
                    "notions": theme.notions(),
                    "prerequis": theme.prerequis(),
                    "difficulte": theme.difficulte(),
                    "mots_cles": theme.mots_cles(),
                },
            )
            compte += 1

        self.stdout.write(
            self.style.SUCCESS(f"  [OK] {compte} thematique(s) importee(s) pour {matiere.nom}")
        )
        return compte
