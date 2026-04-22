"""
Commande d'export du contenu pédagogique en fixture JSON, pour redéploiement
en prod sans avoir à regénérer les leçons / QCM via IA.

Exporte les modèles de l'app `contenu` (Matiere, ChapitreProgramme, Thematique,
Lecon, QuestionQCM, Proposition). Les FK vers `utilisateurs` (Lecon.validee_par)
sont neutralisées : les comptes dev n'existent pas en prod.

Exemples :

    # Par défaut → backend/contenu/fixtures/contenu.json
    #   (loaddata contenu.json le trouve automatiquement)
    python manage.py exporter_contenu

    # Chemin personnalisé
    python manage.py exporter_contenu --sortie chemin/vers/fichier.json
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand


APPS_A_EXPORTER = ["contenu"]

# FK vers utilisateurs à nullifier : les users dev ≠ users prod.
CHAMPS_UTILISATEUR_A_NEUTRALISER = {
    "contenu.lecon": ["validee_par"],
}


class Command(BaseCommand):
    help = (
        "Exporte le contenu pédagogique en fixture JSON "
        "(pour redéploiement en prod sans regénération IA)."
    )

    def add_arguments(self, parser):
        app_contenu = apps.get_app_config("contenu")
        defaut = Path(app_contenu.path) / "fixtures" / "contenu.json"
        parser.add_argument(
            "--sortie",
            type=str,
            default=str(defaut),
            help=f"Chemin du fichier de sortie (défaut : {defaut}).",
        )

    def handle(self, *args, **options):
        chemin = Path(options["sortie"])
        chemin.parent.mkdir(parents=True, exist_ok=True)

        buffer = io.StringIO()
        call_command(
            "dumpdata",
            *APPS_A_EXPORTER,
            indent=2,
            stdout=buffer,
        )
        donnees = json.loads(buffer.getvalue())

        nb_neutralises = 0
        for objet in donnees:
            champs = CHAMPS_UTILISATEUR_A_NEUTRALISER.get(objet["model"])
            if not champs:
                continue
            for champ in champs:
                if objet["fields"].get(champ) is not None:
                    objet["fields"][champ] = None
                    nb_neutralises += 1

        chemin.write_text(
            json.dumps(donnees, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        compteur: dict[str, int] = {}
        for objet in donnees:
            compteur[objet["model"]] = compteur.get(objet["model"], 0) + 1

        self.stdout.write(self.style.SUCCESS(f"Export écrit : {chemin}"))
        for modele, nb in sorted(compteur.items()):
            self.stdout.write(f"  {modele:28s} : {nb:>5d}")
        if nb_neutralises:
            self.stdout.write(
                self.style.WARNING(
                    f"  ({nb_neutralises} FK utilisateur nullifié(s))"
                )
            )
        self.stdout.write("")
        self.stdout.write(
            "Pour charger en prod après migrate :\n"
            f"  python manage.py loaddata {chemin.name}"
        )
