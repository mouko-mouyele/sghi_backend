from django.contrib import admin

from .models import ShiftSchedule


@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'service', 'date_debut', 'date_fin', 'type_garde')
    list_filter = ('type_garde', 'service')
