"""Serializers pour la progression de l'élève."""

from rest_framework import serializers

from contenu.serializers import ThematiqueListSerializer

from .models import ProgressionLecon, ReponseDonnee, TentativeQCM


class ProgressionLeconSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressionLecon
        fields = [
            "id",
            "thematique",
            "lecon_lue",
            "date_debut_lecture",
            "date_fin_lecture",
            "temps_passe_secondes",
        ]
        read_only_fields = ["id"]


class ReponseDonneeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReponseDonnee
        fields = [
            "id",
            "question",
            "proposition_choisie",
            "correcte",
            "date_reponse",
        ]


class TentativeQCMSerializer(serializers.ModelSerializer):
    reponses = ReponseDonneeSerializer(many=True, read_only=True)
    thematique = ThematiqueListSerializer(read_only=True)

    class Meta:
        model = TentativeQCM
        fields = [
            "id",
            "thematique",
            "date_debut",
            "date_fin",
            "score",
            "total_questions",
            "terminee",
            "reponses",
        ]
