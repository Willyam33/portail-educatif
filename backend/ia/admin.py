"""Configuration de l'interface admin pour le suivi des appels à l'API Claude."""

from django.contrib import admin
from django.db.models import Sum

from .models import ConsommationAPI


@admin.register(ConsommationAPI)
class ConsommationAPIAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "type_appel",
        "modele",
        "utilisateur",
        "jetons_entree",
        "jetons_sortie",
        "cout_estime_euros",
    )
    list_filter = ("type_appel", "modele")
    search_fields = ("utilisateur__username", "modele")
    readonly_fields = ("date",)

    def changelist_view(self, request, extra_context=None):
        total = ConsommationAPI.objects.aggregate(total=Sum("cout_estime_euros"))
        extra_context = extra_context or {}
        extra_context["total_cout"] = total["total"] or 0
        return super().changelist_view(request, extra_context=extra_context)
