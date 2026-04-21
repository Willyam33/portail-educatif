"""Routes de l'application utilisateurs (préfixées par /api/v1/ dans portail.urls)."""

from django.urls import path

from .views import LogoutView, MeView

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="auth_me"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
]
