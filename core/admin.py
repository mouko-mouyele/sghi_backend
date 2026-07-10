from django.contrib import admin

from .models import AuditLog, HospitalInfo


@admin.register(HospitalInfo)
class HospitalInfoAdmin(admin.ModelAdmin):
    list_display = ('nom_etablissement', 'telephone', 'updated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action_type', 'model_name', 'object_id', 'user', 'ip_address')
    list_filter = ('action_type', 'model_name')
    readonly_fields = ('user', 'action_type', 'model_name', 'object_id', 'old_value', 'new_value', 'ip_address', 'user_agent', 'timestamp')
    search_fields = ('object_id', 'model_name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
