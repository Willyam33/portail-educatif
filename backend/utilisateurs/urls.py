"""Routes de l'application utilisateurs (préfixées par /api/v1/ dans portail.urls)."""

from django.urls import path

from .parent_views import (
    DetailJourView,
    EnfantsView,
    QuestionsLibresParentView,
    SuiviEleveView,
)
from .views import LogoutView, MeView

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="auth_me"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("parent/enfants/", EnfantsView.as_view(), name="parent_enfants"),
    path(
        "parent/suivi/<int:eleve_id>/",
        SuiviEleveView.as_view(),
        name="parent_suivi",
    ),
    path(
        "parent/suivi/<int:eleve_id>/jour/<str:date>/",
        DetailJourView.as_view(),
        name="parent_detail_jour",
    ),
    path(
        "parent/suivi/<int:eleve_id>/questions-libres/",
        QuestionsLibresParentView.as_view(),
        name="parent_questions_libres",
    ),
]
