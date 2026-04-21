"""Vues API pour l'application utilisateurs."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UtilisateurSerializer


class MeView(APIView):
    """Retourne les informations de l'utilisateur connecté (voir §6.2)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)


class LogoutView(APIView):
    """Invalide le refresh token via la blacklist SimpleJWT (voir §6.2)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "Le champ 'refresh' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)
