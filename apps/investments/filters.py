import django_filters
from apps.investments.models import Asset


class AssetFilter(django_filters.FilterSet):
    class Meta:
        model = Asset
        fields = ("project", "asset_type", "country", "currency")
