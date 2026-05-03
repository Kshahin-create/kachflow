from django.contrib import admin
from apps.integrations.models import ApiConnection, RawApiEvent, SyncLog


@admin.register(ApiConnection)
class ApiConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "project", "status", "last_sync_at", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("name", "project__name")


@admin.register(RawApiEvent)
class RawApiEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "project", "endpoint", "processed", "received_at")
    list_filter = ("provider", "processed")
    search_fields = ("endpoint", "project__name")


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("api_connection", "status", "records_fetched", "records_created", "records_updated", "started_at", "finished_at")
    list_filter = ("status",)
