from django.contrib import admin

from .models import Machine, Manual


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("id", "machine_code", "name", "model")
    search_fields = ("machine_code", "name", "model")


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    list_display = ("id", "document_id", "name", "machine", "revision", "uploaded_at")
    list_filter = ("machine",)
    search_fields = ("document_id", "name")