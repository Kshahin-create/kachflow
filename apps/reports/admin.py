from django.contrib import admin
from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "report_type", "period_start", "period_end", "status", "created_at")
    search_fields = ("title", "project__name")
    list_filter = ("report_type", "status")
    date_hierarchy = "created_at"
