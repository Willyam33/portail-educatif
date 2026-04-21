"""Configuration de l'interface admin Django pour les utilisateurs."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Famille, Utilisateur


@admin.register(Famille)
class FamilleAdmin(admin.ModelAdmin):
    list_display = ("nom", "actif", "date_creation")
    list_filter = ("actif",)
    search_fields = ("nom",)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "famille", "is_active")
    list_filter = ("role", "is_active", "famille")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Portail éducatif",
            {
                "fields": (
                    "role",
                    "date_naissance",
                    "niveau_scolaire",
                    "famille",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Portail éducatif",
            {
                "fields": (
                    "role",
                    "date_naissance",
                    "niveau_scolaire",
                    "famille",
                )
            },
        ),
    )
