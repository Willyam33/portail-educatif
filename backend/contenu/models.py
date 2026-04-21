"""
Modèles pour la gestion du contenu pédagogique (voir spécifications §4.2).

Hiérarchie :
    Matiere → ChapitreProgramme → Thematique → Lecon (1-1) / QuestionQCM → Proposition

Une Thematique correspond à une journée du plan annuel (180 jours).
"""

from django.conf import settings
from django.db import models


class Matiere(models.Model):
    """Matière du programme officiel (Français, Maths, Histoire, …)."""

    code = models.CharField("code", max_length=8, unique=True)
    nom = models.CharField("nom", max_length=80)
    couleur = models.CharField(
        "couleur",
        max_length=7,
        default="#4f46e5",
        help_text="Code hexadécimal utilisé pour l'affichage (ex. #4f46e5).",
    )
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "matière"
        verbose_name_plural = "matières"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class ChapitreProgramme(models.Model):
    """Chapitre du programme officiel, rattaché à une matière."""

    matiere = models.ForeignKey(
        Matiere,
        verbose_name="matière",
        on_delete=models.CASCADE,
        related_name="chapitres",
    )
    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    objectifs = models.TextField(
        "objectifs",
        blank=True,
        help_text="Compétences du Bulletin officiel visées par ce chapitre.",
    )
    ordre_programme = models.PositiveSmallIntegerField("ordre dans le programme", default=0)

    class Meta:
        verbose_name = "chapitre du programme"
        verbose_name_plural = "chapitres du programme"
        ordering = ["matiere__ordre", "ordre_programme"]
        constraints = [
            models.UniqueConstraint(
                fields=["matiere", "titre"],
                name="chapitre_unique_par_matiere",
            )
        ]

    def __str__(self):
        return f"{self.matiere.code} — {self.titre}"


class Thematique(models.Model):
    """Une journée du plan annuel (1 à 180)."""

    class Statut(models.TextChoices):
        PLANIFIEE = "planifiee", "Planifiée"
        GENEREE = "generee", "Générée"
        VALIDEE = "validee", "Validée"
        ARCHIVEE = "archivee", "Archivée"

    numero_jour = models.PositiveSmallIntegerField(
        "numéro de jour global",
        unique=True,
        null=True,
        blank=True,
        help_text="Position dans le plan annuel global (1 à 180). Attribué après import via une commande d'ordonnancement.",
    )
    numero_dans_matiere = models.PositiveSmallIntegerField(
        "numéro dans la matière",
        help_text="Position dans le plan annuel de la matière (numérotation locale du fichier plan_annuel_*.md).",
    )
    titre = models.CharField("titre", max_length=200)
    matiere = models.ForeignKey(
        Matiere,
        verbose_name="matière",
        on_delete=models.PROTECT,
        related_name="thematiques",
    )
    chapitre = models.ForeignKey(
        ChapitreProgramme,
        verbose_name="chapitre",
        on_delete=models.PROTECT,
        related_name="thematiques",
        null=True,
        blank=True,
    )
    objectifs_apprentissage = models.TextField("objectifs d'apprentissage", blank=True)
    notions = models.TextField("notions abordées", blank=True)
    prerequis = models.TextField("pré-requis", blank=True)
    mots_cles = models.JSONField("mots-clés", default=list, blank=True)
    difficulte = models.PositiveSmallIntegerField("difficulté", default=2)
    statut = models.CharField(
        "statut",
        max_length=12,
        choices=Statut.choices,
        default=Statut.PLANIFIEE,
    )
    date_prevue = models.DateField("date prévue", null=True, blank=True)

    class Meta:
        verbose_name = "thématique"
        verbose_name_plural = "thématiques"
        ordering = ["matiere__ordre", "numero_dans_matiere"]
        constraints = [
            models.UniqueConstraint(
                fields=["matiere", "numero_dans_matiere"],
                name="thematique_unique_par_matiere",
            )
        ]

    def __str__(self):
        numero = f"Jour {self.numero_jour} — " if self.numero_jour else ""
        return f"{numero}{self.matiere.code} #{self.numero_dans_matiere} — {self.titre}"


class Lecon(models.Model):
    """Contenu pédagogique Markdown associé à une thématique (voir §4.2)."""

    thematique = models.OneToOneField(
        Thematique,
        verbose_name="thématique",
        on_delete=models.CASCADE,
        related_name="lecon",
    )
    contenu = models.TextField("contenu Markdown")
    mots_cles = models.JSONField("mots-clés", default=list, blank=True)
    duree_lecture_estimee = models.PositiveSmallIntegerField(
        "durée de lecture estimée (minutes)",
        default=10,
    )
    modele_ia_utilise = models.CharField(
        "modèle IA utilisé",
        max_length=80,
        blank=True,
    )
    version_prompt = models.CharField(
        "version du prompt",
        max_length=20,
        blank=True,
        help_text="Version du prompt de génération (voir docs/prompts_ia.md).",
    )
    date_generation = models.DateTimeField("date de génération", auto_now_add=True)
    date_modification = models.DateTimeField("date de modification", auto_now=True)
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="validée par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecons_validees",
    )

    class Meta:
        verbose_name = "leçon"
        verbose_name_plural = "leçons"

    def __str__(self):
        return f"Leçon — {self.thematique}"


class QuestionQCM(models.Model):
    """Question d'un QCM associée à une thématique."""

    thematique = models.ForeignKey(
        Thematique,
        verbose_name="thématique",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    enonce = models.TextField("énoncé")
    difficulte = models.PositiveSmallIntegerField("difficulté", default=2)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)
    explication_generale = models.TextField("explication générale", blank=True)

    class Meta:
        verbose_name = "question de QCM"
        verbose_name_plural = "questions de QCM"
        ordering = ["thematique", "ordre"]
        constraints = [
            models.UniqueConstraint(
                fields=["thematique", "ordre"],
                name="question_ordre_unique_par_thematique",
            )
        ]

    def __str__(self):
        return f"Q{self.ordre} — {self.thematique.titre}"


class Proposition(models.Model):
    """Proposition de réponse à une question de QCM."""

    question = models.ForeignKey(
        QuestionQCM,
        verbose_name="question",
        on_delete=models.CASCADE,
        related_name="propositions",
    )
    texte = models.TextField("texte")
    est_correcte = models.BooleanField("est correcte", default=False)
    explication = models.TextField("explication", blank=True)
    ordre = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "proposition"
        verbose_name_plural = "propositions"
        ordering = ["question", "ordre"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "ordre"],
                name="proposition_ordre_unique_par_question",
            )
        ]

    def __str__(self):
        return self.texte[:60]
