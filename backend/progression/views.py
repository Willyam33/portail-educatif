"""Vues API « progression » — réponses QCM, tentatives, récapitulatif élève."""

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from contenu.models import Proposition, QuestionQCM
from contenu.serializers import (
    CorrectionReponseSerializer,
    PropositionCorrigeeSerializer,
)
from utilisateurs.permissions import EstEleve

from .models import ProgressionLecon, ReponseDonnee, TentativeQCM
from .serializers import TentativeQCMSerializer


class RepondreView(APIView):
    """
    POST /tentatives/<id>/repondre/

    Body attendu : { "question_id": int, "proposition_choisie_id": int }
    Retourne la correction immédiate (bonne/mauvaise + toutes les explications).
    """

    permission_classes = [EstEleve]

    def post(self, request, tentative_id):
        tentative = get_object_or_404(
            TentativeQCM, pk=tentative_id, eleve=request.user
        )
        if tentative.terminee:
            return Response(
                {"detail": "Cette tentative est déjà terminée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question_id = request.data.get("question_id")
        proposition_id = request.data.get("proposition_choisie_id")
        if not question_id or not proposition_id:
            return Response(
                {"detail": "Champs 'question_id' et 'proposition_choisie_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = get_object_or_404(
            QuestionQCM, pk=question_id, thematique=tentative.thematique
        )
        proposition = get_object_or_404(
            Proposition, pk=proposition_id, question=question
        )

        reponse, cree = ReponseDonnee.objects.update_or_create(
            tentative=tentative,
            question=question,
            defaults={
                "proposition_choisie": proposition,
                "correcte": proposition.est_correcte,
            },
        )

        data = {
            "question_id": question.id,
            "proposition_choisie_id": proposition.id,
            "correcte": reponse.correcte,
            "explication_generale": question.explication_generale,
            "propositions": PropositionCorrigeeSerializer(
                question.propositions.order_by("ordre"), many=True
            ).data,
        }
        return Response(CorrectionReponseSerializer(data).data)


class TerminerTentativeView(APIView):
    """POST /tentatives/<id>/terminer/ — calcule le score et clôture."""

    permission_classes = [EstEleve]

    def post(self, request, tentative_id):
        tentative = get_object_or_404(
            TentativeQCM, pk=tentative_id, eleve=request.user
        )
        if tentative.terminee:
            return Response(TentativeQCMSerializer(tentative).data)

        score = tentative.reponses.filter(correcte=True).count()
        tentative.score = score
        tentative.total_questions = tentative.thematique.questions.count()
        tentative.terminee = True
        tentative.date_fin = timezone.now()
        tentative.save(update_fields=["score", "total_questions", "terminee", "date_fin"])
        return Response(TentativeQCMSerializer(tentative).data)


class HistoriqueTentativesView(APIView):
    """GET /tentatives/ — tentatives terminées de l'élève, plus récentes d'abord."""

    permission_classes = [EstEleve]

    def get(self, request):
        tentatives = (
            TentativeQCM.objects.filter(eleve=request.user, terminee=True)
            .select_related("thematique__matiere")
            .order_by("-date_fin")[:50]
        )
        return Response(TentativeQCMSerializer(tentatives, many=True).data)


class ProgressionMeView(APIView):
    """GET /progression/moi/ — récapitulatif global de l'élève."""

    permission_classes = [EstEleve]

    def get(self, request):
        lecons_lues = ProgressionLecon.objects.filter(
            eleve=request.user, lecon_lue=True
        ).count()
        tentatives_qs = TentativeQCM.objects.filter(
            eleve=request.user, terminee=True
        )
        nb_tentatives = tentatives_qs.count()
        score_moyen = None
        if nb_tentatives:
            agregat = tentatives_qs.aggregate(
                total_score=Avg("score"),
                total_questions=Avg("total_questions"),
            )
            if agregat["total_questions"]:
                score_moyen = round(
                    100 * agregat["total_score"] / agregat["total_questions"], 1
                )
        par_matiere = list(
            tentatives_qs.values("thematique__matiere__code", "thematique__matiere__nom")
            .annotate(
                nb=Count("id"),
                nb_reussies=Count("id", filter=Q(score__gte=1)),
            )
            .order_by("thematique__matiere__ordre")
        )
        return Response(
            {
                "lecons_lues": lecons_lues,
                "qcm_termines": nb_tentatives,
                "score_moyen_pourcent": score_moyen,
                "par_matiere": par_matiere,
            }
        )
