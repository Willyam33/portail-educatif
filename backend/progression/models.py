"""
Modèles pour le suivi de la progression des élèves (voir spécifications §4.3).
"""

from django.conf import settings
from django.db import models


class ProgressionLecon(models.Model):
    """Suivi de la lecture d'une leçon par un élève."""

    eleve = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="élève",
        on_delete=models.CASCADE,
        related_name="progressions_lecon",
    )
    thematique = models.ForeignKey(
        "contenu.Thematique",
        verbose_name="thématique",
        on_delete=models.CASCADE,
        related_name="progressions",
    )
    lecon_lue = models.BooleanField("leçon lue", default=False)
    date_debut_lecture = models.DateTimeField("début de lecture", null=True, blank=True)
    date_fin_lecture = models.DateTimeField("fin de lecture", null=True, blank=True)
    temps_passe_secondes = models.PositiveIntegerField("temps passé (s)", default=0)

    class Meta:
        verbose_name = "progression leçon"
        verbose_name_plural = "progressions leçons"
        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "thematique"],
                name="progression_unique_par_eleve_thematique",
            )
        ]

    def __str__(self):
        return f"{self.eleve} — {self.thematique}"


class TentativeQCM(models.Model):
    """Une passation de QCM par un élève."""

    eleve = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="élève",
        on_delete=models.CASCADE,
        related_name="tentatives_qcm",
    )
    thematique = models.ForeignKey(
        "contenu.Thematique",
        verbose_name="thématique",
        on_delete=models.CASCADE,
        related_name="tentatives",
    )
    date_debut = models.DateTimeField("début", auto_now_add=True)
    date_fin = models.DateTimeField("fin", null=True, blank=True)
    score = models.PositiveSmallIntegerField("score", default=0)
    total_questions = models.PositiveSmallIntegerField("total questions", default=0)
    terminee = models.BooleanField("terminée", default=False)

    class Meta:
        verbose_name = "tentative de QCM"
        verbose_name_plural = "tentatives de QCM"
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.eleve} — {self.thematique} — {self.score}/{self.total_questions}"


class ReponseDonnee(models.Model):
    """Réponse d'un élève à une question au sein d'une tentative."""

    tentative = models.ForeignKey(
        TentativeQCM,
        verbose_name="tentative",
        on_delete=models.CASCADE,
        related_name="reponses",
    )
    question = models.ForeignKey(
        "contenu.QuestionQCM",
        verbose_name="question",
        on_delete=models.CASCADE,
        related_name="reponses_donnees",
    )
    proposition_choisie = models.ForeignKey(
        "contenu.Proposition",
        verbose_name="proposition choisie",
        on_delete=models.PROTECT,
        related_name="reponses_donnees",
    )
    correcte = models.BooleanField("correcte", default=False)
    date_reponse = models.DateTimeField("date de réponse", auto_now_add=True)

    class Meta:
        verbose_name = "réponse donnée"
        verbose_name_plural = "réponses données"
        ordering = ["date_reponse"]
        constraints = [
            models.UniqueConstraint(
                fields=["tentative", "question"],
                name="reponse_unique_par_tentative_question",
            )
        ]

    def __str__(self):
        return f"{self.tentative_id} — Q{self.question.ordre}"


class QuestionLibre(models.Model):
    """Question libre posée par un élève à l'IA dans le contexte d'une leçon."""

    eleve = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="élève",
        on_delete=models.CASCADE,
        related_name="questions_libres",
    )
    thematique = models.ForeignKey(
        "contenu.Thematique",
        verbose_name="thématique (contexte)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_libres",
    )
    question = models.TextField("question")
    reponse = models.TextField("réponse", blank=True)
    date = models.DateTimeField("date", auto_now_add=True)
    jetons_entree = models.PositiveIntegerField("jetons d'entrée", default=0)
    jetons_sortie = models.PositiveIntegerField("jetons de sortie", default=0)

    class Meta:
        verbose_name = "question libre"
        verbose_name_plural = "questions libres"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.eleve} — {self.date:%Y-%m-%d %H:%M}"
