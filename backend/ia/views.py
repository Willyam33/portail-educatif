"""Vues API « ia » — questions libres de l'élève."""

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from contenu.models import Thematique
from contenu.views import STATUTS_CONSULTABLES
from progression.models import QuestionLibre
from utilisateurs.permissions import EstEleve

from .prompts import MESSAGE_LIMITE_QUOTIDIENNE_ATTEINTE
from .serializers import QuestionLibreSerializer
from .services import QuestionLibreError, ServiceClaude


class QuestionsLibresView(APIView):
    """
    GET  /eleve/thematiques/<id>/questions-libres/
        → historique des questions déjà posées sur cette thématique.
    POST /eleve/thematiques/<id>/questions-libres/
        body: { "question": "..." }
        → création d'une question + réponse IA (limite 5/jour).
    """

    permission_classes = [EstEleve]

    def get(self, request, thematique_id):
        thematique = get_object_or_404(
            Thematique.objects.filter(statut__in=STATUTS_CONSULTABLES),
            pk=thematique_id,
        )
        questions = QuestionLibre.objects.filter(
            eleve=request.user, thematique=thematique
        ).order_by("date")
        return Response(
            {
                "questions": QuestionLibreSerializer(questions, many=True).data,
                "nb_restantes_aujourdhui": self._nb_restantes(request.user),
                "max_par_jour": settings.QUESTIONS_LIBRES_MAX_PAR_JOUR,
            }
        )

    def post(self, request, thematique_id):
        thematique = get_object_or_404(
            Thematique.objects.filter(
                statut__in=STATUTS_CONSULTABLES
            ).select_related("matiere"),
            pk=thematique_id,
        )
        question = (request.data.get("question") or "").strip()
        if not question:
            return Response(
                {"detail": "Le champ 'question' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(question) > 1000:
            return Response(
                {"detail": "Ta question est trop longue (max 1000 caractères)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if self._nb_restantes(request.user) <= 0:
            return Response(
                {"detail": MESSAGE_LIMITE_QUOTIDIENNE_ATTEINTE},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            service = ServiceClaude()
            resultat = service.repondre_question_libre(
                question=question, thematique=thematique, eleve=request.user,
            )
        except QuestionLibreError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "question": QuestionLibreSerializer(resultat.question_libre).data,
                "filtree": resultat.filtree,
                "nb_restantes_aujourdhui": self._nb_restantes(request.user),
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _nb_restantes(eleve) -> int:
        debut_jour = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        nb_aujourdhui = QuestionLibre.objects.filter(
            eleve=eleve, date__gte=debut_jour,
        ).count()
        return max(0, settings.QUESTIONS_LIBRES_MAX_PAR_JOUR - nb_aujourdhui)
