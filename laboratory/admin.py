from django.contrib import admin

from .models import LabOrder, LabResult, LabResultAudit, LabTestCatalog


@admin.register(LabTestCatalog)
class LabTestCatalogAdmin(admin.ModelAdmin):
    list_display = ('code', 'libelle', 'prix', 'delai_heures')


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('patient', 'examen', 'statut', 'date_commande')
    list_filter = ('statut',)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('commande', 'valeur', 'valide', 'valide_par')


admin.site.register(LabResultAudit)
