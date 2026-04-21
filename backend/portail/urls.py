"""
Routes racine du projet.

Toutes les routes API sont préfixées par /api/v1/ (voir spécifications §6.1).
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def ping(_request):
    """Route de santé pour vérifier la communication front/back."""
    return JsonResponse({"statut": "ok", "service": "portail-educatif", "version": "0.1.0"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/ping/", ping, name="ping"),
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("utilisateurs.urls")),
]
