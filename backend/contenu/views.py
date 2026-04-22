"""Vues API « contenu » pour l'espace élève."""

from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from progression.models import ProgressionLecon, TentativeQCM
from utilisateurs.permissions import EstEleve

from .models import Lecon, Matiere, Thematique
from .serializers import (
    LeconSerializer,
    MatiereAvecThematiquesSerializer,
    QuestionElevesSerializer,
    ThematiqueDetailSerializer,
    ThematiqueListSerializer,
)


STATUTS_CONSULTABLES = {
    Thematique.Statut.GENEREE,
    Thematique.Statut.VALIDEE,
}


def _thematiques_accessibles(eleve):
    """
    Thématiques que l'élève peut consulter : celles dont le contenu est prêt
    (généré ou validé) et dont numero_jour est attribué.
    """
    return Thematique.objects.filter(
        statut__in=STATUTS_CONSULTABLES,
        numero_jour__isnull=False,
    ).select_related("matiere")


def _jour_courant(eleve) -> int:
    """
    Retourne le numéro de jour que l'élève doit travailler aujourd'hui.

    Stratégie : la plus petite thématique accessible dont l'élève n'a pas
    encore de tentative QCM terminée. Si tout est validé, on renvoie la
    dernière thématique disponible.
    """
    jours_termines = set(
        TentativeQCM.objects.filter(eleve=eleve, terminee=True).values_list(
            "thematique__numero_jour", flat=True
        )
    )
    accessibles = _thematiques_accessibles(eleve).order_by("numero_jour")
    for t in accessibles:
        if t.numero_jour not in jours_termines:
            return t.numero_jour
    dernier = accessibles.last()
    return dernier.numero_jour if dernier else 1


class ThematiqueDuJourView(APIView):
    """Retourne la thématique que l'élève doit travailler aujourd'hui."""

    permission_classes = [EstEleve]

    def get(self, request):
        jour = _jour_courant(request.user)
        thematique = _thematiques_accessibles(request.user).filter(numero_jour=jour).first()
        if thematique is None:
            return Response(
                {"detail": "Aucune thématique disponible."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ThematiqueDetailSerializer(thematique).data
        data["jour_courant"] = jour
        data["lecon_disponible"] = hasattr(thematique, "lecon")
        data["qcm_disponible"] = thematique.questions.exists()
        return Response(data)


class LeconView(APIView):
    """GET /thematiques/<id>/lecon/ — contenu Markdown d'une leçon."""

    permission_classes = [EstEleve]

    def get(self, request, thematique_id):
        thematique = get_object_or_404(
            _thematiques_accessibles(request.user), pk=thematique_id
        )
        lecon = getattr(thematique, "lecon", None)
        if lecon is None:
            return Response(
                {"detail": "Aucune leçon pour cette thématique."},
                status=status.HTTP_404_NOT_FOUND,
            )

        progression, _ = ProgressionLecon.objects.get_or_create(
            eleve=request.user,
            thematique=thematique,
        )
        if progression.date_debut_lecture is None:
            progression.date_debut_lecture = timezone.now()
            progression.save(update_fields=["date_debut_lecture"])

        return Response(
            {
                "thematique": ThematiqueDetailSerializer(thematique).data,
                "lecon": LeconSerializer(lecon).data,
                "deja_lue": progression.lecon_lue,
            }
        )


class MarquerLeconLueView(APIView):
    """POST /thematiques/<id>/lecon/marquer-lue/"""

    permission_classes = [EstEleve]

    def post(self, request, thematique_id):
        thematique = get_object_or_404(
            _thematiques_accessibles(request.user), pk=thematique_id
        )
        progression, _ = ProgressionLecon.objects.get_or_create(
            eleve=request.user,
            thematique=thematique,
        )
        if not progression.lecon_lue:
            progression.lecon_lue = True
            progression.date_fin_lecture = timezone.now()
            progression.save(update_fields=["lecon_lue", "date_fin_lecture"])
        return Response({"lecon_lue": True})


class MatieresVueEleveView(APIView):
    """
    GET /eleve/matieres/ — retourne les 7 matières du programme avec, pour
    chacune, la liste de ses thématiques. Inclut toutes les thématiques du
    programme (même celles dont la leçon n'est pas encore générée), avec un
    flag `lecon_disponible` / `qcm_disponible` pour piloter l'UI.
    """

    permission_classes = [EstEleve]

    def get(self, request):
        thematiques = (
            Thematique.objects.select_related("matiere")
            .prefetch_related("lecon", "questions")
            .order_by("matiere__ordre", "numero_dans_matiere")
        )

        # Progression de l'élève pour afficher les petits badges "fait/en cours".
        progressions_lecon = {
            p.thematique_id: p.lecon_lue
            for p in ProgressionLecon.objects.filter(eleve=request.user)
        }
        qcm_termines = set(
            TentativeQCM.objects.filter(eleve=request.user, terminee=True).values_list(
                "thematique_id", flat=True
            )
        )

        par_matiere: dict[int, list[Thematique]] = defaultdict(list)
        for t in thematiques:
            par_matiere[t.matiere_id].append(t)

        matieres = Matiere.objects.order_by("ordre")
        resultat = []
        for matiere in matieres:
            liste = par_matiere.get(matiere.id, [])
            resultat.append(
                {
                    "matiere": matiere,
                    "thematiques": [
                        {
                            "id": t.id,
                            "numero_dans_matiere": t.numero_dans_matiere,
                            "numero_jour": t.numero_jour,
                            "titre": t.titre,
                            "difficulte": t.difficulte,
                            "statut": t.statut,
                            "lecon_disponible": (
                                hasattr(t, "lecon") and t.statut in STATUTS_CONSULTABLES
                            ),
                            "qcm_disponible": (
                                t.questions.exists() and t.statut in STATUTS_CONSULTABLES
                            ),
                            "lecon_lue": progressions_lecon.get(t.id, False),
                            "qcm_termine": t.id in qcm_termines,
                        }
                        for t in liste
                    ],
                }
            )

        return Response(MatiereAvecThematiquesSerializer(resultat, many=True).data)


class QCMView(APIView):
    """
    GET /thematiques/<id>/qcm/ — lance (ou reprend) une tentative QCM.
    Les bonnes réponses ne sont PAS exposées ici.
    """

    permission_classes = [EstEleve]

    def get(self, request, thematique_id):
        thematique = get_object_or_404(
            _thematiques_accessibles(request.user), pk=thematique_id
        )
        questions = thematique.questions.prefetch_related("propositions").order_by("ordre")
        if not questions.exists():
            return Response(
                {"detail": "Aucune question pour cette thématique."},
                status=status.HTTP_404_NOT_FOUND,
            )

        tentative = (
            TentativeQCM.objects.filter(
                eleve=request.user, thematique=thematique, terminee=False
            )
            .order_by("-date_debut")
            .first()
        )
        if tentative is None:
            tentative = TentativeQCM.objects.create(
                eleve=request.user,
                thematique=thematique,
                total_questions=questions.count(),
            )

        reponses_deja_donnees = {
            r.question_id: {
                "proposition_choisie_id": r.proposition_choisie_id,
                "correcte": r.correcte,
            }
            for r in tentative.reponses.all()
        }

        return Response(
            {
                "tentative_id": tentative.id,
                "thematique": ThematiqueDetailSerializer(thematique).data,
                "questions": QuestionElevesSerializer(questions, many=True).data,
                "reponses_deja_donnees": reponses_deja_donnees,
            }
        )
