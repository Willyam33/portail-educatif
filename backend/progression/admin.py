"""Configuration de l'interface admin pour le suivi de progression."""

from django.contrib import admin

from .models import ProgressionLecon, QuestionLibre, ReponseDonnee, TentativeQCM


@admin.register(ProgressionLecon)
class ProgressionLeconAdmin(admin.ModelAdmin):
    list_display = ("eleve", "thematique", "lecon_lue", "temps_passe_secondes")
    list_filter = ("lecon_lue", "thematique__matiere")
    search_fields = ("eleve__username", "thematique__titre")


class ReponseInline(admin.TabularInline):
    model = ReponseDonnee
    extra = 0
    readonly_fields = ("question", "proposition_choisie", "correcte", "date_reponse")


@admin.register(TentativeQCM)
class TentativeQCMAdmin(admin.ModelAdmin):
    list_display = ("eleve", "thematique", "score", "total_questions", "terminee", "date_debut")
    list_filter = ("terminee", "thematique__matiere")
    search_fields = ("eleve__username", "thematique__titre")
    inlines = [ReponseInline]


@admin.register(QuestionLibre)
class QuestionLibreAdmin(admin.ModelAdmin):
    list_display = ("eleve", "thematique", "date", "jetons_entree", "jetons_sortie")
    list_filter = ("thematique__matiere",)
    search_fields = ("eleve__username", "question", "reponse")
    readonly_fields = ("date",)
