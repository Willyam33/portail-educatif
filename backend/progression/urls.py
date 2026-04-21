"""Routes de l'application « progression » côté élève."""

from django.urls import path

from .views import (
    HistoriqueTentativesView,
    ProgressionMeView,
    RepondreView,
    TerminerTentativeView,
)

urlpatterns = [
    path(
        "eleve/tentatives/<int:tentative_id>/repondre/",
        RepondreView.as_view(),
        name="eleve_repondre",
    ),
    path(
        "eleve/tentatives/<int:tentative_id>/terminer/",
        TerminerTentativeView.as_view(),
        name="eleve_terminer_tentative",
    ),
    path(
        "eleve/tentatives/",
        HistoriqueTentativesView.as_view(),
        name="eleve_historique_tentatives",
    ),
    path(
        "eleve/progression/",
        ProgressionMeView.as_view(),
        name="eleve_progression",
    ),
]
