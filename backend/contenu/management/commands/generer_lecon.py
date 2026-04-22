"""
Commande de génération de leçons via Claude Sonnet 4.6 (voir docs/prompts_ia.md).

Exemples d'utilisation :

    # Une seule thématique (par id ou par jour global)
    python manage.py generer_lecon --thematique 3
    python manage.py generer_lecon --jour 5

    # Toutes les thématiques de français, 10 max, qui n'ont pas encore de leçon
    python manage.py generer_lecon --matiere FR --nb 10

    # Régénérer une plage de jours même si la leçon existe
    python manage.py generer_lecon --jours 1-10 --force

    # Simulation sans appel API
    python manage.py generer_lecon --matiere all --nb 5 --dry-run
"""

from __future__ import annotations

import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from ia.services import GenerationError, ServiceClaude

from ._helpers_generation import (
    ajouter_arguments_selection,
    libelle_thematique,
    resoudre_thematiques,
)


class Command(BaseCommand):
    help = "Génère les leçons Markdown pour les thématiques ciblées via Claude."

    def add_arguments(self, parser):
        ajouter_arguments_selection(parser)
        parser.add_argument(
            "--pause",
            type=float,
            default=1.0,
            help="Pause (en secondes) entre deux appels pour éviter les rate limits.",
        )

    def handle(self, *args, **options):
        thematiques = list(resoudre_thematiques(options))
        if not thematiques:
            self.stdout.write(self.style.WARNING("Aucune thématique cible."))
            return

        force = options["force"]
        if not force:
            thematiques = [t for t in thematiques if not hasattr(t, "lecon")]

        if not thematiques:
            self.stdout.write(
                self.style.SUCCESS("Toutes les thématiques cibles ont déjà une leçon.")
            )
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"== {len(thematiques)} leçon(s) à générer"
            )
        )
        for t in thematiques:
            self.stdout.write(f"  - {libelle_thematique(t)}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Mode dry-run : pas d'appel API."))
            return

        service = ServiceClaude()
        total_cout = Decimal("0")
        total_in = 0
        total_out = 0
        echecs: list[tuple[str, str]] = []

        for index, thematique in enumerate(thematiques, start=1):
            libelle = libelle_thematique(thematique)
            self.stdout.write(f"\n[{index}/{len(thematiques)}] {libelle}")
            try:
                resultat = service.generer_lecon(thematique)
            except GenerationError as exc:
                self.stdout.write(self.style.ERROR(f"  echec : {exc}"))
                echecs.append((libelle, str(exc)))
                continue

            total_in += resultat.jetons_entree
            total_out += resultat.jetons_sortie
            total_cout += resultat.cout_eur
            self.stdout.write(
                self.style.SUCCESS(
                    f"  OK — {resultat.jetons_entree}+{resultat.jetons_sortie} jetons — "
                    f"{resultat.cout_eur} €"
                )
            )

            if index < len(thematiques) and options["pause"] > 0:
                time.sleep(options["pause"])

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"== Terminé : {len(thematiques) - len(echecs)}/{len(thematiques)} "
                f"leçons générées — {total_in} jetons in, {total_out} out, {total_cout} € au total"
            )
        )
        if echecs:
            self.stdout.write(self.style.ERROR(f"Échecs : {len(echecs)}"))
            for libelle, raison in echecs:
                self.stdout.write(f"  - {libelle} : {raison}")
