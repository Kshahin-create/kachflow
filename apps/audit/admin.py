from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "project", "action", "object_type", "object_id")
    search_fields = ("user__username", "project__name", "action", "description")
    list_filter = ("action", "object_type")
    date_hierarchy = "created_at"
    readonly_fields = ("metadata",)
