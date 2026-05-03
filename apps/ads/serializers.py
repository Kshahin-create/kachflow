from rest_framework import serializers
from apps.ads.models import AdAccount, Campaign, AdSpendDaily, AdPerformanceMetric


class AdAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdAccount
        fields = "__all__"


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = "__all__"


class AdSpendDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdSpendDaily
        fields = "__all__"


class AdPerformanceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdPerformanceMetric
        fields = "__all__"
