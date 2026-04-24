"""Vues API « progression » — réponses QCM, tentatives, récapitulatif élève."""

from django.db.models import Avg, Count, Exists, OuterRef, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from contenu.models import Lecon, Matiere, Proposition, QuestionQCM, Thematique
from contenu.serializers import (
    CorrectionReponseSerializer,
    MatiereSerializer,
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
        total_lecons = Lecon.objects.count()
        total_qcm = Thematique.objects.annotate(
            has_qcm=Exists(QuestionQCM.objects.filter(thematique=OuterRef("pk")))
        ).filter(has_qcm=True).count()

        return Response(
            {
                "lecons_lues": lecons_lues,
                "total_lecons": total_lecons,
                "qcm_termines": nb_tentatives,
                "total_qcm": total_qcm,
                "score_moyen_pourcent": score_moyen,
                "par_matiere": par_matiere,
            }
        )


class ProgressionDetailleeView(APIView):
    """
    GET /eleve/progression/detail/

    Renvoie, pour chaque matière, les indicateurs détaillés :
    - nombre de leçons lues,
    - nombre de QCM terminés,
    - score moyen (en pourcentage),
    - meilleur/pire score.
    """

    permission_classes = [EstEleve]

    def get(self, request):
        matieres = Matiere.objects.all().order_by("ordre")

        tentatives_par_matiere = {
            row["thematique__matiere_id"]: row
            for row in (
                TentativeQCM.objects.filter(eleve=request.user, terminee=True)
                .values("thematique__matiere_id")
                .annotate(
                    nb_qcm=Count("id"),
                    total_score=Sum("score"),
                    total_questions=Sum("total_questions"),
                )
            )
        }
        lecons_par_matiere = {
            row["thematique__matiere_id"]: row["nb"]
            for row in (
                ProgressionLecon.objects.filter(eleve=request.user, lecon_lue=True)
                .values("thematique__matiere_id")
                .annotate(nb=Count("id"))
            )
        }
        total_lecons_par_matiere = dict(
            Lecon.objects.values_list("thematique__matiere_id")
            .annotate(nb=Count("id"))
            .values_list("thematique__matiere_id", "nb")
        )
        total_qcm_par_matiere = dict(
            Thematique.objects.annotate(
                has_qcm=Exists(QuestionQCM.objects.filter(thematique=OuterRef("pk")))
            )
            .filter(has_qcm=True)
            .values_list("matiere_id")
            .annotate(nb=Count("id"))
            .values_list("matiere_id", "nb")
        )

        resultat = []
        for matiere in matieres:
            stats = tentatives_par_matiere.get(matiere.id)
            nb_qcm = stats["nb_qcm"] if stats else 0
            total_questions = stats["total_questions"] if stats else 0
            total_score = stats["total_score"] if stats else 0
            score_pourcent = (
                round(100 * total_score / total_questions, 1)
                if total_questions
                else None
            )
            resultat.append(
                {
                    "matiere": MatiereSerializer(matiere).data,
                    "lecons_lues": lecons_par_matiere.get(matiere.id, 0),
                    "total_lecons": total_lecons_par_matiere.get(matiere.id, 0),
                    "qcm_termines": nb_qcm,
                    "total_qcm": total_qcm_par_matiere.get(matiere.id, 0),
                    "score_moyen_pourcent": score_pourcent,
                }
            )
        return Response({"par_matiere": resultat})


class HistoriqueThematiquesView(APIView):
    """
    GET /eleve/historique-thematiques/

    Liste de toutes les thématiques sur lesquelles l'élève a une trace
    (leçon lue et/ou QCM terminé), plus récentes d'abord.
    """

    permission_classes = [EstEleve]

    def get(self, request):
        # On part des thématiques ayant au moins une trace (leçon ou tentative).
        tentatives = {
            t.thematique_id: t
            for t in TentativeQCM.objects.filter(
                eleve=request.user, terminee=True
            ).select_related("thematique__matiere")
        }
        progressions = {
            p.thematique_id: p
            for p in ProgressionLecon.objects.filter(
                eleve=request.user, lecon_lue=True
            ).select_related("thematique__matiere")
        }

        thematiques_ids = set(tentatives) | set(progressions)
        entrees = []
        for tid in thematiques_ids:
            tentative = tentatives.get(tid)
            progression = progressions.get(tid)
            thematique = (tentative or progression).thematique
            date_ref = (
                tentative.date_fin
                if tentative and tentative.date_fin
                else progression.date_fin_lecture if progression
                else None
            )
            entrees.append(
                {
                    "thematique_id": thematique.id,
                    "titre": thematique.titre,
                    "numero_jour": thematique.numero_jour,
                    "matiere": MatiereSerializer(thematique.matiere).data,
                    "lecon_lue": progression is not None,
                    "qcm_termine": tentative is not None,
                    "score": tentative.score if tentative else None,
                    "total_questions": tentative.total_questions if tentative else None,
                    "date": date_ref,
                }
            )
        entrees.sort(key=lambda e: e["date"] or timezone.now(), reverse=True)
        return Response(entrees)
