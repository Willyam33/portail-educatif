"""
Modèles pour la gestion des utilisateurs (voir spécifications §4.1).

Hiérarchie : une Famille regroupe des Utilisateurs (élèves, parents). Les
administrateurs ne sont rattachés à aucune famille.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Famille(models.Model):
    """Cellule familiale regroupant élèves et parents."""

    nom = models.CharField("nom", max_length=150)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "famille"
        verbose_name_plural = "familles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Utilisateur(AbstractUser):
    """Utilisateur du portail : élève, parent ou administrateur."""

    class Role(models.TextChoices):
        ELEVE = "eleve", "Élève"
        PARENT = "parent", "Parent"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    role = models.CharField(
        "rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.ELEVE,
    )
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    niveau_scolaire = models.CharField("niveau scolaire", max_length=10, default="3e")
    famille = models.ForeignKey(
        Famille,
        verbose_name="famille",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membres",
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["last_name", "first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def est_eleve(self):
        return self.role == self.Role.ELEVE

    @property
    def est_parent(self):
        return self.role == self.Role.PARENT

    @property
    def est_administrateur(self):
        return self.role == self.Role.ADMINISTRATEUR or self.is_superuser
