from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginJournal, RefreshToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SGHL', {'fields': ('role', 'phone', 'specialty', 'mfa_enabled', 'is_active_staff')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('SGHL', {'fields': ('role', 'email', 'first_name', 'last_name')}),
    )


@admin.register(LoginJournal)
class LoginJournalAdmin(admin.ModelAdmin):
    list_display = ('user', 'success', 'ip_address', 'timestamp')
    list_filter = ('success',)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'revoked', 'created_at')
    list_filter = ('revoked',)
