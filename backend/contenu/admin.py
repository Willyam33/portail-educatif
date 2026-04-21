"""Configuration de l'interface admin pour le contenu pédagogique."""

from django.contrib import admin

from .models import (
    ChapitreProgramme,
    Lecon,
    Matiere,
    Proposition,
    QuestionQCM,
    Thematique,
)


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "ordre", "couleur")
    list_editable = ("ordre", "couleur")
    search_fields = ("code", "nom")


@admin.register(ChapitreProgramme)
class ChapitreProgrammeAdmin(admin.ModelAdmin):
    list_display = ("titre", "matiere", "ordre_programme")
    list_filter = ("matiere",)
    search_fields = ("titre",)


class PropositionInline(admin.TabularInline):
    model = Proposition
    extra = 0
    fields = ("ordre", "texte", "est_correcte", "explication")


@admin.register(QuestionQCM)
class QuestionQCMAdmin(admin.ModelAdmin):
    list_display = ("thematique", "ordre", "difficulte")
    list_filter = ("difficulte", "thematique__matiere")
    search_fields = ("enonce", "thematique__titre")
    inlines = [PropositionInline]


class QuestionInline(admin.TabularInline):
    model = QuestionQCM
    extra = 0
    fields = ("ordre", "enonce", "difficulte")
    show_change_link = True


@admin.register(Thematique)
class ThematiqueAdmin(admin.ModelAdmin):
    list_display = ("numero_jour", "titre", "matiere", "difficulte", "statut", "date_prevue")
    list_filter = ("statut", "matiere", "difficulte")
    search_fields = ("titre", "objectifs_apprentissage", "notions")
    ordering = ("numero_jour",)
    inlines = [QuestionInline]


@admin.register(Lecon)
class LeconAdmin(admin.ModelAdmin):
    list_display = ("thematique", "modele_ia_utilise", "date_generation", "validee_par")
    list_filter = ("modele_ia_utilise", "validee_par")
    search_fields = ("thematique__titre", "contenu")
    autocomplete_fields = ("thematique", "validee_par")
