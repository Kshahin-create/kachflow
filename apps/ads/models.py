from django.db import models


class AdAccount(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="ad_accounts")
    platform = models.CharField(max_length=80)
    account_name = models.CharField(max_length=180)
    account_id = models.CharField(max_length=120, blank=True)
    currency = models.CharField(max_length=8, default="SAR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Campaign(models.Model):
    ad_account = models.ForeignKey(AdAccount, on_delete=models.CASCADE, related_name="campaigns")
    campaign_name = models.CharField(max_length=180)
    campaign_id = models.CharField(max_length=120, blank=True)
    objective = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class AdSet(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="adsets")
    name = models.CharField(max_length=180)
    adset_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Ad(models.Model):
    adset = models.ForeignKey(AdSet, on_delete=models.CASCADE, related_name="ads")
    name = models.CharField(max_length=180)
    ad_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class AdSpendDaily(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="ad_spend_daily")
    ad_account = models.ForeignKey(AdAccount, on_delete=models.CASCADE, related_name="daily_spend")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField()
    spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    leads = models.PositiveIntegerField(default=0)
    orders = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="SAR")
    source = models.CharField(max_length=80, default="manual")
    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class AdPerformanceMetric(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="ad_metrics")
    date = models.DateField()
    spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    orders = models.PositiveIntegerField(default=0)
    leads = models.PositiveIntegerField(default=0)
    cpa = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    roas = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    roi = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    ctr = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cpc = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cpm = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
