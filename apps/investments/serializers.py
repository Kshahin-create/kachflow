from rest_framework import serializers
from apps.investments.models import Asset, InvestmentTransaction, InvestmentIncome


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"


class InvestmentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentTransaction
        fields = "__all__"


class InvestmentIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentIncome
        fields = "__all__"
