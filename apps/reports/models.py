from django.conf import settings
from django.db import models


class Report(models.Model):
    REPORT_TYPES = [
        ("monthly_financial", "Monthly Financial"),
        ("project_profit_loss", "Project Profit/Loss"),
        ("cash_position", "Cash Position"),
        ("ecommerce_performance", "Ecommerce Performance"),
        ("real_estate_collections", "Real Estate Collections"),
        ("ads_performance", "Ads Performance"),
        ("investments", "Investments"),
        ("partners", "Partners"),
        ("investors", "Investors"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, blank=True, null=True, related_name="reports")
    report_type = models.CharField(max_length=60, choices=REPORT_TYPES)
    title = models.CharField(max_length=180)
    period_start = models.DateField()
    period_end = models.DateField()
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)
    file = models.FileField(upload_to="reports/", blank=True, null=True)
    status = models.CharField(max_length=40, default="generated")
    created_at = models.DateTimeField(auto_now_add=True)
