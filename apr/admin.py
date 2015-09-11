from django.contrib import admin
from .models import RegistryEntry, EncObs, ArvTherapy

class ArvTherapyInline(admin.TabularInline):
    model = ArvTherapy

class RegistryEntryAdmin(admin.ModelAdmin):
    model = RegistryEntry
    list_display = ('apr_id', 'site', 'cohort_date')
    list_filter = ('site', 'voided')
    inlines = [ArvTherapyInline,]

class EncObs(admin.ModelAdmin):
    model = EncObs

admin.site.register(RegistryEntry, RegistryEntryAdmin)
#admin.site.register()
