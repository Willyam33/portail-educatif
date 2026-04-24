"""
Vues API de l'espace parent (voir specs §6.4).

Un parent peut consulter les enfants rattachés à sa famille :
- liste de ses enfants,
- tableau de bord de suivi d'un enfant (stats globales + par matière),
- détail d'une journée particulière,
- historique des questions libres posées par l'enfant.
"""

from __future__ import annotations

from datetime import datetime

from django.db.models import Count, Exists, OuterRef, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from contenu.models import Lecon, Matiere, QuestionQCM, Thematique
from contenu.serializers import (
    MatiereSerializer,
    ThematiqueDetailSerializer,
)
from progression.models import (
    ProgressionLecon,
    QuestionLibre,
    TentativeQCM,
)

from .models import Utilisateur
from .permissions import EstParentOuAdmin, peut_consulter_eleve


def _get_enfant_ou_403(request, eleve_id) -> Utilisateur:
    """Récupère l'élève cible ou lève une exception DRF si non autorisé."""
    eleve = get_object_or_404(Utilisateur, pk=eleve_id, role=Utilisateur.Role.ELEVE)
    if not peut_consulter_eleve(request.user, eleve):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("Cet élève n'est pas rattaché à votre famille.")
    return eleve


class EnfantsView(APIView):
    """GET /parent/enfants/ — enfants rattachés à la famille du parent connecté."""

    permission_classes = [EstParentOuAdmin]

    def get(self, request):
        user = request.user
        if user.est_administrateur:
            enfants = Utilisateur.objects.filter(role=Utilisateur.Role.ELEVE).order_by(
                "last_name", "first_name"
            )
        else:
            if user.famille_id is None:
                return Response([])
            enfants = Utilisateur.objects.filter(
                role=Utilisateur.Role.ELEVE, famille_id=user.famille_id
            ).order_by("last_name", "first_name")
        data = [
            {
                "id": e.id,
                "username": e.username,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "niveau_scolaire": e.niveau_scolaire,
            }
            for e in enfants
        ]
        return Response(data)


class SuiviEleveView(APIView):
    """GET /parent/suivi/<eleve_id>/ — tableau de bord de l'enfant."""

    permission_classes = [EstParentOuAdmin]

    def get(self, request, eleve_id):
        eleve = _get_enfant_ou_403(request, eleve_id)

        tentatives_qs = TentativeQCM.objects.filter(eleve=eleve, terminee=True)
        nb_tentatives = tentatives_qs.count()
        lecons_lues = ProgressionLecon.objects.filter(
            eleve=eleve, lecon_lue=True
        ).count()

        score_moyen = None
        if nb_tentatives:
            agregat = tentatives_qs.aggregate(
                total_score=Sum("score"),
                total_questions=Sum("total_questions"),
            )
            if agregat["total_questions"]:
                score_moyen = round(
                    100 * agregat["total_score"] / agregat["total_questions"], 1
                )

        # Stats par matière — utile pour repérer les matières en difficulté.
        tentatives_par_matiere = {
            row["thematique__matiere_id"]: row
            for row in (
                tentatives_qs.values("thematique__matiere_id")
                .annotate(
                    nb=Count("id"),
                    total_score=Sum("score"),
                    total_questions=Sum("total_questions"),
                )
            )
        }
        lecons_par_matiere = {
            row["thematique__matiere_id"]: row["nb"]
            for row in (
                ProgressionLecon.objects.filter(eleve=eleve, lecon_lue=True)
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

        par_matiere = []
        for matiere in Matiere.objects.all().order_by("ordre"):
            stats = tentatives_par_matiere.get(matiere.id)
            total_q = stats["total_questions"] if stats else 0
            total_s = stats["total_score"] if stats else 0
            par_matiere.append(
                {
                    "matiere": MatiereSerializer(matiere).data,
                    "lecons_lues": lecons_par_matiere.get(matiere.id, 0),
                    "total_lecons": total_lecons_par_matiere.get(matiere.id, 0),
                    "qcm_termines": stats["nb"] if stats else 0,
                    "total_qcm": total_qcm_par_matiere.get(matiere.id, 0),
                    "score_moyen_pourcent": (
                        round(100 * total_s / total_q, 1) if total_q else None
                    ),
                }
            )

        total_lecons = Lecon.objects.count()
        total_qcm = sum(total_qcm_par_matiere.values())

        nb_questions_libres = QuestionLibre.objects.filter(eleve=eleve).count()

        return Response(
            {
                "eleve": {
                    "id": eleve.id,
                    "username": eleve.username,
                    "first_name": eleve.first_name,
                    "last_name": eleve.last_name,
                },
                "lecons_lues": lecons_lues,
                "total_lecons": total_lecons,
                "qcm_termines": nb_tentatives,
                "total_qcm": total_qcm,
                "score_moyen_pourcent": score_moyen,
                "nb_questions_libres": nb_questions_libres,
                "par_matiere": par_matiere,
            }
        )


class DetailJourView(APIView):
    """
    GET /parent/suivi/<eleve_id>/jour/<date>/
    date au format YYYY-MM-DD. Le « jour » ici = date de fin de tentative OU
    date de fin de lecture. On renvoie, pour cette journée, ce que l'enfant
    a effectivement fait (leçon, QCM, questions libres).
    """

    permission_classes = [EstParentOuAdmin]

    def get(self, request, eleve_id, date):
        eleve = _get_enfant_ou_403(request, eleve_id)
        try:
            jour = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Format de date attendu : AAAA-MM-JJ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        debut = timezone.make_aware(datetime.combine(jour, datetime.min.time()))
        fin = timezone.make_aware(datetime.combine(jour, datetime.max.time()))

        tentatives = (
            TentativeQCM.objects.filter(
                eleve=eleve, terminee=True, date_fin__range=(debut, fin)
            )
            .select_related("thematique__matiere")
            .order_by("date_fin")
        )
        lectures = (
            ProgressionLecon.objects.filter(
                eleve=eleve, lecon_lue=True, date_fin_lecture__range=(debut, fin)
            )
            .select_related("thematique__matiere")
            .order_by("date_fin_lecture")
        )
        questions = (
            QuestionLibre.objects.filter(eleve=eleve, date__range=(debut, fin))
            .select_related("thematique__matiere")
            .order_by("date")
        )

        # Regroupement par thématique pour un rendu plus lisible côté front.
        thematiques = {}
        for p in lectures:
            t = p.thematique
            thematiques.setdefault(t.id, {"thematique": t, "lecture": None, "tentative": None, "questions": []})
            thematiques[t.id]["lecture"] = {
                "date_fin_lecture": p.date_fin_lecture,
                "temps_passe_secondes": p.temps_passe_secondes,
            }
        for tt in tentatives:
            t = tt.thematique
            thematiques.setdefault(t.id, {"thematique": t, "lecture": None, "tentative": None, "questions": []})
            thematiques[t.id]["tentative"] = {
                "score": tt.score,
                "total_questions": tt.total_questions,
                "date_fin": tt.date_fin,
            }
        for q in questions:
            t = q.thematique
            if t is None:
                continue
            thematiques.setdefault(t.id, {"thematique": t, "lecture": None, "tentative": None, "questions": []})
            thematiques[t.id]["questions"].append(
                {
                    "id": q.id,
                    "question": q.question,
                    "reponse": q.reponse,
                    "date": q.date,
                }
            )

        data = []
        for entree in thematiques.values():
            data.append(
                {
                    "thematique": ThematiqueDetailSerializer(entree["thematique"]).data,
                    "lecture": entree["lecture"],
                    "tentative": entree["tentative"],
                    "questions": entree["questions"],
                }
            )
        return Response({"date": date, "activites": data})


class QuestionsLibresParentView(APIView):
    """GET /parent/suivi/<eleve_id>/questions-libres/ — historique complet."""

    permission_classes = [EstParentOuAdmin]

    def get(self, request, eleve_id):
        eleve = _get_enfant_ou_403(request, eleve_id)
        questions = (
            QuestionLibre.objects.filter(eleve=eleve)
            .select_related("thematique__matiere")
            .order_by("-date")[:200]
        )
        data = [
            {
                "id": q.id,
                "question": q.question,
                "reponse": q.reponse,
                "date": q.date,
                "thematique": (
                    {
                        "id": q.thematique.id,
                        "titre": q.thematique.titre,
                        "matiere": MatiereSerializer(q.thematique.matiere).data,
                    }
                    if q.thematique
                    else None
                ),
            }
            for q in questions
        ]
        return Response(data)
