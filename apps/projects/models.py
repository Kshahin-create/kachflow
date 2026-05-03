from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    name = models.CharField(max_length=180)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_companies")
    country = models.CharField(max_length=80, blank=True)
    base_currency = models.CharField(max_length=8, default="SAR")
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class Project(TimeStampedModel):
    class ProjectType(models.TextChoices):
        ECOMMERCE = "ecommerce", "Ecommerce"
        REAL_ESTATE = "real_estate", "Real Estate"
        LEASING = "leasing", "Leasing"
        FINANCE = "finance", "Finance"
        INVESTMENT = "investment", "Investment"
        ADS = "ads", "Ads"
        WAREHOUSE = "warehouse", "Warehouse"
        OFFICE = "office", "Office"
        GENERIC = "generic", "Generic"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=180)
    project_type = models.CharField(max_length=32, choices=ProjectType.choices, default=ProjectType.GENERIC)
    country = models.CharField(max_length=80, blank=True)
    base_currency = models.CharField(max_length=8, default="SAR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    logo = models.ImageField(upload_to="project_logos/", blank=True, null=True)
    description = models.TextField(blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProjectSetting(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField(max_length=100)
    value = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("project", "key")

    def __str__(self):
        return f"{self.project}: {self.key}"
