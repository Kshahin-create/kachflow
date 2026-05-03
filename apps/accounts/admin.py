from django.contrib import admin
from apps.accounts.models import ProjectInvitation, ProjectMember, ProjectStakeholder, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "preferred_language", "timezone", "is_active", "created_at")
    search_fields = ("user__username", "user__email", "phone")
    list_filter = ("is_active", "preferred_language")


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "role", "dashboard_access", "is_active", "created_at")
    search_fields = ("user__username", "project__name")
    list_filter = ("role", "dashboard_access", "is_active")


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "project", "role", "accepted_at", "expires_at", "created_at")
    search_fields = ("email", "project__name")
    list_filter = ("role", "dashboard_access")
    readonly_fields = ("token", "created_at")


@admin.register(ProjectStakeholder)
class ProjectStakeholderAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "ownership_percentage", "profit_share_percentage")
    search_fields = ("project__name", "user__username")
