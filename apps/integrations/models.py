from django.conf import settings
from django.db import models


class ApiConnection(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="api_connections")
    provider = models.CharField(max_length=80)
    name = models.CharField(max_length=180)
    credentials = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=40, default="draft")
    last_sync_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class RawApiEvent(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="raw_api_events")
    provider = models.CharField(max_length=80)
    endpoint = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class SyncLog(models.Model):
    api_connection = models.ForeignKey(ApiConnection, on_delete=models.CASCADE, related_name="sync_logs")
    status = models.CharField(max_length=40)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    records_fetched = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
