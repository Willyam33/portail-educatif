"""Routes de l'application « ia » (questions libres)."""

from django.urls import path

from .views import QuestionsLibresView

urlpatterns = [
    path(
        "eleve/thematiques/<int:thematique_id>/questions-libres/",
        QuestionsLibresView.as_view(),
        name="eleve_questions_libres",
    ),
]
