from django.contrib import admin

from .models import Dispensation, Medication, PatientPharmacyRequest, StockLot, StockMovement


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'categorie', 'prix_unitaire', 'seuil_alerte')
    list_filter = ('categorie',)


@admin.register(PatientPharmacyRequest)
class PatientPharmacyRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'patient', 'statut', 'created_at')
    list_filter = ('statut',)


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ('medicament', 'numero_lot', 'quantite', 'date_peremption')


admin.site.register(StockMovement)
admin.site.register(Dispensation)
