from django.contrib import admin

from .models import (
    Bed, Building, Consultation, Hospitalization, HospitalService,
    MedicalDocument, NursingCare, Patient, Prescription, Room, VitalSign,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('numero_dossier', 'nom', 'prenom', 'date_naissance', 'sexe')
    search_fields = ('nom', 'prenom', 'numero_dossier')


class BedInline(admin.TabularInline):
    model = Bed
    extra = 1


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    inlines = [BedInline]
    list_display = ('numero', 'service', 'capacite')


@admin.register(HospitalService)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'building')


@admin.register(Hospitalization)
class HospitalizationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'lit', 'statut', 'date_entree', 'medecin_referent')
    list_filter = ('statut',)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medecin', 'diagnostic_cim10', 'validee', 'date_consultation')


admin.site.register(Building)
admin.site.register(Bed)
admin.site.register(Prescription)
admin.site.register(VitalSign)
admin.site.register(NursingCare)
admin.site.register(MedicalDocument)
