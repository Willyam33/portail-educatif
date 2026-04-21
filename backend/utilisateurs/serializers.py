"""Serializers DRF pour l'application utilisateurs."""

from rest_framework import serializers

from .models import Famille, Utilisateur


class FamilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Famille
        fields = ["id", "nom", "actif", "date_creation"]
        read_only_fields = ["id", "date_creation"]


class UtilisateurSerializer(serializers.ModelSerializer):
    """Profil affiché à l'utilisateur connecté (/auth/me/)."""

    famille = FamilleSerializer(read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "date_naissance",
            "niveau_scolaire",
            "famille",
            "date_creation",
        ]
        read_only_fields = ["id", "role", "famille", "date_creation"]
