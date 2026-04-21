"""
Modèle de suivi des appels à l'API Claude (voir spécifications §4.4).
"""

from django.conf import settings
from django.db import models


class ConsommationAPI(models.Model):
    """Enregistrement d'un appel à l'API Anthropic, utilisé pour le suivi des coûts."""

    class TypeAppel(models.TextChoices):
        GENERATION_LECON = "generation_lecon", "Génération de leçon"
        GENERATION_QCM = "generation_qcm", "Génération de QCM"
        QUESTION_LIBRE = "question_libre", "Question libre"
        AUTRE = "autre", "Autre"

    date = models.DateTimeField("date", auto_now_add=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consommations_api",
    )
    type_appel = models.CharField(
        "type d'appel",
        max_length=20,
        choices=TypeAppel.choices,
    )
    modele = models.CharField("modèle", max_length=80)
    jetons_entree = models.PositiveIntegerField("jetons d'entrée", default=0)
    jetons_sortie = models.PositiveIntegerField("jetons de sortie", default=0)
    cout_estime_euros = models.DecimalField(
        "coût estimé (€)",
        max_digits=8,
        decimal_places=4,
        default=0,
    )

    class Meta:
        verbose_name = "consommation API"
        verbose_name_plural = "consommations API"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%Y-%m-%d %H:%M} — {self.get_type_appel_display()} — {self.cout_estime_euros} €"
