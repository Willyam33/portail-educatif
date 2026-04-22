"""Permissions DRF spécifiques au portail."""

from rest_framework.permissions import BasePermission


class EstEleve(BasePermission):
    """L'utilisateur doit être authentifié et avoir le rôle « élève »."""

    message = "Cette ressource est réservée aux élèves."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.est_eleve)


class EstParentOuAdmin(BasePermission):
    """L'utilisateur doit être parent ou administrateur."""

    message = "Cette ressource est réservée aux parents et administrateurs."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.est_parent or user.est_administrateur)
        )


def peut_consulter_eleve(user, eleve) -> bool:
    """
    Un parent ne peut consulter qu'un enfant rattaché à sa famille.
    Les administrateurs peuvent tout consulter.
    """
    if not (user and user.is_authenticated):
        return False
    if user.est_administrateur:
        return True
    if user.est_parent and eleve.famille_id is not None:
        return user.famille_id == eleve.famille_id
    return False
