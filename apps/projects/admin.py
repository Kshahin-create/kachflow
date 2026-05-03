from django.contrib import admin
from apps.projects.models import Company, Project, ProjectSetting


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "country", "base_currency", "created_at")
    search_fields = ("name", "owner__username")
    list_filter = ("country", "base_currency")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "project_type", "status", "base_currency", "created_at")
    search_fields = ("name", "company__name")
    list_filter = ("project_type", "status", "base_currency")
    date_hierarchy = "created_at"


@admin.register(ProjectSetting)
class ProjectSettingAdmin(admin.ModelAdmin):
    list_display = ("project", "key", "updated_at")
    search_fields = ("project__name", "key")
