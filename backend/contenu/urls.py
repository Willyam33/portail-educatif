"""Routes de l'application « contenu » côté élève."""

from django.urls import path

from .views import (
    LeconView,
    MarquerLeconLueView,
    MatieresVueEleveView,
    QCMView,
    ThematiqueDuJourView,
)

urlpatterns = [
    path(
        "eleve/thematique-du-jour/",
        ThematiqueDuJourView.as_view(),
        name="eleve_thematique_du_jour",
    ),
    path(
        "eleve/matieres/",
        MatieresVueEleveView.as_view(),
        name="eleve_matieres",
    ),
    path(
        "eleve/thematiques/<int:thematique_id>/lecon/",
        LeconView.as_view(),
        name="eleve_lecon",
    ),
    path(
        "eleve/thematiques/<int:thematique_id>/lecon/marquer-lue/",
        MarquerLeconLueView.as_view(),
        name="eleve_marquer_lecon_lue",
    ),
    path(
        "eleve/thematiques/<int:thematique_id>/qcm/",
        QCMView.as_view(),
        name="eleve_qcm",
    ),
]
