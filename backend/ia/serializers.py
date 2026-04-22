"""Serializers de l'app IA (questions libres)."""

from rest_framework import serializers

from progression.models import QuestionLibre


class QuestionLibreSerializer(serializers.ModelSerializer):
    """Question libre + réponse renvoyées au front."""

    class Meta:
        model = QuestionLibre
        fields = ["id", "question", "reponse", "date"]
