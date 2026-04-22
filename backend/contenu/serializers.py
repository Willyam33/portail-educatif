"""Serializers pour les ressources pédagogiques exposées aux élèves."""

from rest_framework import serializers

from .models import Lecon, Matiere, Proposition, QuestionQCM, Thematique


class MatiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matiere
        fields = ["id", "code", "nom", "couleur", "ordre"]


class ThematiqueListSerializer(serializers.ModelSerializer):
    """Vue condensée pour les listes (calendrier, historique)."""

    matiere = MatiereSerializer(read_only=True)
    a_lecon = serializers.SerializerMethodField()

    class Meta:
        model = Thematique
        fields = [
            "id",
            "numero_jour",
            "numero_dans_matiere",
            "titre",
            "matiere",
            "statut",
            "difficulte",
            "a_lecon",
        ]

    def get_a_lecon(self, obj) -> bool:
        return hasattr(obj, "lecon")


class ThematiqueDetailSerializer(serializers.ModelSerializer):
    """Détail d'une thématique (page leçon)."""

    matiere = MatiereSerializer(read_only=True)

    class Meta:
        model = Thematique
        fields = [
            "id",
            "numero_jour",
            "numero_dans_matiere",
            "titre",
            "matiere",
            "objectifs_apprentissage",
            "notions",
            "prerequis",
            "mots_cles",
            "difficulte",
            "statut",
        ]


class LeconSerializer(serializers.ModelSerializer):
    """Leçon exposée à l'élève : on ne renvoie jamais les méta-IA internes."""

    class Meta:
        model = Lecon
        fields = [
            "id",
            "contenu",
            "mots_cles",
            "duree_lecture_estimee",
            "date_modification",
        ]


class PropositionSansReponseSerializer(serializers.ModelSerializer):
    """Propositions vues côté élève : sans `est_correcte` ni explication."""

    class Meta:
        model = Proposition
        fields = ["id", "texte", "ordre"]


class QuestionElevesSerializer(serializers.ModelSerializer):
    """Questions exposées avant réponse : on masque la bonne réponse."""

    propositions = PropositionSansReponseSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionQCM
        fields = ["id", "enonce", "ordre", "difficulte", "propositions"]


class PropositionCorrigeeSerializer(serializers.ModelSerializer):
    """Propositions renvoyées après réponse (mode correction)."""

    class Meta:
        model = Proposition
        fields = ["id", "texte", "ordre", "est_correcte", "explication"]


class CorrectionReponseSerializer(serializers.Serializer):
    """Résultat renvoyé après un POST sur /repondre/."""

    question_id = serializers.IntegerField()
    proposition_choisie_id = serializers.IntegerField()
    correcte = serializers.BooleanField()
    explication_generale = serializers.CharField()
    propositions = PropositionCorrigeeSerializer(many=True)


class ThematiqueEnMenuSerializer(serializers.Serializer):
    """Thématique dans le menu « Explorer par matière »."""

    id = serializers.IntegerField()
    numero_dans_matiere = serializers.IntegerField()
    numero_jour = serializers.IntegerField(allow_null=True)
    titre = serializers.CharField()
    difficulte = serializers.IntegerField()
    statut = serializers.CharField()
    lecon_disponible = serializers.BooleanField()
    qcm_disponible = serializers.BooleanField()
    lecon_lue = serializers.BooleanField()
    qcm_termine = serializers.BooleanField()


class MatiereAvecThematiquesSerializer(serializers.Serializer):
    """Matière + ses thématiques pour le menu élève."""

    matiere = MatiereSerializer()
    thematiques = ThematiqueEnMenuSerializer(many=True)
