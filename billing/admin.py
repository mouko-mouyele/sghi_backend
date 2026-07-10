from django.contrib import admin

from .models import AccountingJournal, Insurance, Invoice, InvoiceLine, MobileMoneyTransaction, Payment, PatientInsurance


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceLineInline]
    list_display = ('numero', 'patient', 'statut', 'montant_total', 'montant_paye')


admin.site.register(Insurance)
admin.site.register(PatientInsurance)
admin.site.register(Payment)
admin.site.register(MobileMoneyTransaction)
admin.site.register(AccountingJournal)
