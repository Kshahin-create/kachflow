import secrets
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default="ar")
    timezone = models.CharField(max_length=80, default="Asia/Riyadh")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_username()


class ProjectMember(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        PROJECT_MANAGER = "project_manager", "Project Manager"
        ACCOUNTANT = "accountant", "Accountant"
        PARTNER = "partner", "Partner"
        INVESTOR = "investor", "Investor"
        VIEWER = "viewer", "Viewer"

    class DashboardAccess(models.TextChoices):
        FULL = "full", "Full"
        PARTNER = "partner", "Partner"
        FINANCIAL = "financial", "Financial"
        READONLY = "readonly", "Readonly"
        CUSTOM = "custom", "Custom"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)
    dashboard_access = models.CharField(max_length=20, choices=DashboardAccess.choices, default=DashboardAccess.READONLY)
    can_view_dashboard = models.BooleanField(default=True)
    can_view_financials = models.BooleanField(default=False)
    can_view_sensitive_accounts = models.BooleanField(default=False)
    can_view_raw_excel = models.BooleanField(default=False)
    can_upload_excel = models.BooleanField(default=False)
    can_import_data = models.BooleanField(default=False)
    can_add_transactions = models.BooleanField(default=False)
    can_edit_transactions = models.BooleanField(default=False)
    can_delete_transactions = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_view_customers = models.BooleanField(default=False)
    can_view_suppliers = models.BooleanField(default=False)
    can_view_profit = models.BooleanField(default=False)
    can_view_partner_dashboard = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="sent_project_invites")

    class Meta:
        unique_together = ("user", "project")
        indexes = [models.Index(fields=["user", "project", "is_active"])]

    def __str__(self):
        return f"{self.user} - {self.project} ({self.role})"


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class ProjectInvitation(models.Model):
    email = models.EmailField()
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="invitations")
    role = models.CharField(max_length=32, choices=ProjectMember.Role.choices, default=ProjectMember.Role.VIEWER)
    dashboard_access = models.CharField(max_length=20, choices=ProjectMember.DashboardAccess.choices, default=ProjectMember.DashboardAccess.READONLY)
    token = models.CharField(max_length=80, unique=True, default=secrets.token_urlsafe)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="project_invitations")
    accepted_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.email} -> {self.project}"


class ProjectStakeholder(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="stakeholders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_stakes")
    ownership_percentage = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    capital_contribution = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit_share_percentage = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user} stake in {self.project}"
