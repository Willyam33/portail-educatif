"""
Commande de seed : crée une leçon + un QCM de démo pour tester le flux élève.

Cible par défaut la thématique du jour 1 (si elle existe). On peut spécifier
un autre jour via --jour N. Crée également un utilisateur élève de démo si
aucun n'existe, pour permettre un test end-to-end immédiat.

Exemples :

    python manage.py seed_lecon_pilote
    python manage.py seed_lecon_pilote --jour 3
    python manage.py seed_lecon_pilote --eleve ines --mdp motdepasse123
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contenu.models import Lecon, Proposition, QuestionQCM, Thematique

Utilisateur = get_user_model()


CONTENU_MARKDOWN = """\
# La phrase simple et la phrase complexe

Bienvenue dans cette leçon pilote ! Elle illustre le fonctionnement du
portail : lecture, puis QCM, puis retour sur le tableau de bord.

## Objectifs

- Savoir identifier une **phrase simple** et une **phrase complexe**.
- Reconnaître les différents types de propositions.
- Utiliser correctement la coordination et la subordination.

## 1. Définitions

Une **phrase simple** contient un seul verbe conjugué (et donc une seule
proposition). Exemple :

> Le chat dort sur le canapé.

Une **phrase complexe** contient plusieurs verbes conjugués (et donc
plusieurs propositions). Exemple :

> Le chat dort sur le canapé *pendant que* le chien joue dans le jardin.

## 2. Les trois types de propositions

Dans une phrase complexe, les propositions peuvent être reliées de trois
manières :

1. **Juxtaposition** — séparées par une virgule, un point-virgule ou deux
   points : *Il pleut, je reste à la maison.*
2. **Coordination** — reliées par une conjonction de coordination (mais,
   ou, et, donc, or, ni, car) : *Il pleut **mais** je sors quand même.*
3. **Subordination** — une proposition dépend d'une autre par une
   conjonction de subordination (que, quand, parce que, si…) :
   *Je sors **parce que** j'ai besoin d'air.*

## 3. Astuce

Pour savoir si une phrase est simple ou complexe, **compte les verbes
conjugués** : un seul → simple ; plusieurs → complexe.

## À retenir

- Phrase simple = 1 verbe conjugué.
- Phrase complexe = plusieurs verbes conjugués reliés par juxtaposition,
  coordination ou subordination.

Bonne lecture, et bon QCM !
"""


QUESTIONS_QCM = [
    {
        "enonce": "Qu'est-ce qui caractérise une phrase simple ?",
        "explication": "Une phrase simple ne contient qu'une seule proposition, donc un seul verbe conjugué.",
        "propositions": [
            {
                "texte": "Elle contient un seul verbe conjugué.",
                "correcte": True,
                "explication": "Exact : un seul verbe conjugué = une seule proposition = phrase simple.",
            },
            {
                "texte": "Elle se termine par un point d'exclamation.",
                "correcte": False,
                "explication": "La ponctuation finale n'a rien à voir avec la simplicité de la phrase.",
            },
            {
                "texte": "Elle commence toujours par un sujet.",
                "correcte": False,
                "explication": "Beaucoup de phrases commencent par un complément ou un adverbe.",
            },
            {
                "texte": "Elle contient moins de dix mots.",
                "correcte": False,
                "explication": "La longueur ne détermine pas si une phrase est simple ou complexe.",
            },
        ],
    },
    {
        "enonce": "Dans la phrase : *Il pleut, je reste à la maison.*, comment les propositions sont-elles reliées ?",
        "explication": "Les deux propositions sont séparées par une virgule, sans conjonction : c'est une juxtaposition.",
        "propositions": [
            {
                "texte": "Par juxtaposition.",
                "correcte": True,
                "explication": "Oui : virgule, point-virgule ou deux points = juxtaposition.",
            },
            {
                "texte": "Par coordination.",
                "correcte": False,
                "explication": "La coordination nécessite une conjonction comme « mais », « et »…",
            },
            {
                "texte": "Par subordination.",
                "correcte": False,
                "explication": "La subordination implique une conjonction comme « parce que », « quand »…",
            },
            {
                "texte": "Elles ne sont pas reliées.",
                "correcte": False,
                "explication": "Elles sont reliées, justement par la virgule (juxtaposition).",
            },
        ],
    },
    {
        "enonce": "Quelle conjonction introduit une proposition subordonnée ?",
        "explication": "« Parce que » est une conjonction de subordination.",
        "propositions": [
            {
                "texte": "mais",
                "correcte": False,
                "explication": "« mais » est une conjonction de coordination.",
            },
            {
                "texte": "et",
                "correcte": False,
                "explication": "« et » est une conjonction de coordination.",
            },
            {
                "texte": "parce que",
                "correcte": True,
                "explication": "Exact : « parce que » introduit une subordonnée.",
            },
            {
                "texte": "ou",
                "correcte": False,
                "explication": "« ou » est une conjonction de coordination.",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Crée une leçon + QCM de démo et (si besoin) un élève pilote."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jour",
            type=int,
            default=1,
            help="Numéro de jour global de la thématique cible (défaut 1).",
        )
        parser.add_argument(
            "--eleve",
            type=str,
            default="ines",
            help="Nom d'utilisateur de l'élève pilote (défaut : ines).",
        )
        parser.add_argument(
            "--mdp",
            type=str,
            default="pilote1234",
            help="Mot de passe de l'élève pilote (défaut : pilote1234).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        jour = options["jour"]
        username = options["eleve"]
        mdp = options["mdp"]

        thematique = Thematique.objects.filter(numero_jour=jour).first()
        if thematique is None:
            raise CommandError(
                f"Aucune thématique trouvée pour le jour {jour}. "
                "Lance d'abord `python manage.py ordonnancer_jours`."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"== Seed pilote sur jour {jour} : {thematique.matiere.code} — {thematique.titre}"
            )
        )

        # 1) Leçon
        lecon, cree = Lecon.objects.update_or_create(
            thematique=thematique,
            defaults={
                "contenu": CONTENU_MARKDOWN,
                "mots_cles": ["phrase simple", "phrase complexe", "proposition"],
                "duree_lecture_estimee": 8,
                "modele_ia_utilise": "seed-manuel",
                "version_prompt": "pilote-0.1",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  [{'creee' if cree else 'mise a jour'}] Lecon id={lecon.id}"
            )
        )

        # 2) QCM : on efface les anciennes questions pour garantir l'idempotence
        thematique.questions.all().delete()
        for ordre, q in enumerate(QUESTIONS_QCM, start=1):
            question = QuestionQCM.objects.create(
                thematique=thematique,
                enonce=q["enonce"],
                difficulte=2,
                ordre=ordre,
                explication_generale=q["explication"],
            )
            for ordre_prop, prop in enumerate(q["propositions"], start=1):
                Proposition.objects.create(
                    question=question,
                    texte=prop["texte"],
                    est_correcte=prop["correcte"],
                    explication=prop["explication"],
                    ordre=ordre_prop,
                )
        self.stdout.write(
            self.style.SUCCESS(f"  [OK] {len(QUESTIONS_QCM)} questions QCM creees")
        )

        # 3) Marquer la thématique comme validée
        thematique.statut = Thematique.Statut.VALIDEE
        thematique.save(update_fields=["statut"])

        # 4) Élève pilote
        eleve, cree = Utilisateur.objects.get_or_create(
            username=username,
            defaults={
                "first_name": username.capitalize(),
                "role": Utilisateur.Role.ELEVE,
                "niveau_scolaire": "3e",
            },
        )
        if cree:
            eleve.set_password(mdp)
            eleve.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [OK] Eleve pilote cree : username={username} / mot de passe={mdp}"
                )
            )
        else:
            self.stdout.write(f"  Eleve {username} deja existant, mot de passe inchange.")

        self.stdout.write(self.style.SUCCESS("Seed pilote termine."))
