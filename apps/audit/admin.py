from django.contrib import admin
from apps.audit.models import AuditLog, DatabaseBackup


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "project", "action", "object_type", "object_id")
    search_fields = ("user__username", "project__name", "action", "description")
    list_filter = ("action", "object_type")
    date_hierarchy = "created_at"
    readonly_fields = ("metadata",)


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ("created_at", "created_by", "label", "size_bytes", "sha256")
    search_fields = ("label", "sha256", "created_by__username")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "created_by", "label", "size_bytes", "sha256", "payload_gzip")
