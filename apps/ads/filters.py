import django_filters
from apps.ads.models import AdSpendDaily


class AdSpendDailyFilter(django_filters.FilterSet):
    class Meta:
        model = AdSpendDaily
        fields = ("project", "ad_account", "campaign", "date")
