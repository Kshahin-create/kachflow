from django.conf import settings
from django.db import models


class Asset(models.Model):
    ASSET_TYPES = [
        ("real_estate", "Real Estate"), ("business_stake", "Business Stake"), ("stock", "Stock"),
        ("fund", "Fund"), ("gold", "Gold"), ("cash", "Cash"), ("crypto", "Crypto"),
        ("private_investment", "Private Investment"), ("other", "Other"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, blank=True, null=True, related_name="assets")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assets")
    asset_name = models.CharField(max_length=180)
    asset_type = models.CharField(max_length=40, choices=ASSET_TYPES, default="other")
    country = models.CharField(max_length=80, blank=True)
    currency = models.CharField(max_length=8, default="SAR")
    acquisition_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ownership_percentage = models.DecimalField(max_digits=7, decimal_places=4, default=100)
    income_generated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    acquisition_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class InvestmentTransaction(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    transaction_type = models.CharField(max_length=60)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="SAR")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class InvestmentIncome(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="income")
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="SAR")
    income_type = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
