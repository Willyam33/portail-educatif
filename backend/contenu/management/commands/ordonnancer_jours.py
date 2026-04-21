"""
Commande d'ordonnancement des thématiques sur le calendrier annuel (1 à 180).

Après l'import des plans annuels (`importer_plan_annuel`), chaque Thematique
porte son `numero_dans_matiere` mais pas encore de `numero_jour`. Cette
commande répartit les 180 thématiques en entrelaçant les matières selon
leur poids (nombre de thématiques).

Stratégie : pour chaque Thematique, on calcule sa position idéale relative
((index - 0.5) / nombre_themes_matiere) ; on trie toutes les thématiques par
position idéale et on leur attribue numero_jour = 1..180. Cela donne un
calendrier où les matières se succèdent harmonieusement (ex. Français,
Maths, Physique, Maths, …) plutôt que par blocs.

Exemple d'utilisation :

    python manage.py ordonnancer_jours
    python manage.py ordonnancer_jours --dry-run
    python manage.py ordonnancer_jours --reset
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from contenu.models import Thematique


class Command(BaseCommand):
    help = "Attribue numero_jour (1..N) aux thématiques en entrelaçant les matières."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche l'ordre calculé sans écrire en base.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Réinitialise tous les numero_jour à NULL avant recalcul.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        reset = options.get("reset", False)

        thematiques = list(
            Thematique.objects.select_related("matiere").order_by(
                "matiere__ordre", "numero_dans_matiere"
            )
        )
        if not thematiques:
            self.stdout.write(self.style.WARNING("Aucune thématique à ordonnancer."))
            return

        # Comptage par matière pour calculer la position idéale.
        total_par_matiere: dict[int, int] = {}
        for t in thematiques:
            total_par_matiere[t.matiere_id] = total_par_matiere.get(t.matiere_id, 0) + 1

        # On attribue à chaque thématique une "fraction" sur [0, 1] selon sa
        # position dans sa matière, puis on trie par fraction croissante.
        # En cas d'égalité, on départage par ordre de matière pour la stabilité.
        classement = sorted(
            thematiques,
            key=lambda t: (
                (t.numero_dans_matiere - 0.5) / total_par_matiere[t.matiere_id],
                t.matiere.ordre,
                t.matiere_id,
            ),
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"== Ordonnancement de {len(classement)} thématique(s)"
            )
        )

        if dry_run:
            for jour, t in enumerate(classement, start=1):
                self.stdout.write(
                    f"  Jour {jour:>3} — {t.matiere.code:<5} #{t.numero_dans_matiere:>2} — {t.titre[:70]}"
                )
            self.stdout.write(self.style.SUCCESS("Mode --dry-run : aucune écriture."))
            return

        with transaction.atomic():
            if reset:
                Thematique.objects.update(numero_jour=None)
            else:
                # On efface uniquement les numero_jour qui existent déjà pour
                # éviter la contrainte d'unicité pendant la réassignation.
                Thematique.objects.filter(numero_jour__isnull=False).update(
                    numero_jour=None
                )

            for jour, t in enumerate(classement, start=1):
                t.numero_jour = jour
                t.save(update_fields=["numero_jour"])

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] {len(classement)} thematique(s) ordonnancee(s) (jour 1 a {len(classement)})."
            )
        )

        # Petit résumé par matière pour vérifier visuellement la répartition.
        premiers = {}
        for t in classement:
            if t.matiere.code not in premiers:
                premiers[t.matiere.code] = []
            if len(premiers[t.matiere.code]) < 3:
                premiers[t.matiere.code].append(
                    f"J{classement.index(t) + 1}"
                )
        self.stdout.write("  Premiers jours par matiere :")
        for code, jours in premiers.items():
            self.stdout.write(f"    {code:<5} : {', '.join(jours)} ...")
