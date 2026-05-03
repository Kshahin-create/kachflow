import django_filters
from apps.real_estate.models import Lease


class LeaseFilter(django_filters.FilterSet):
    class Meta:
        model = Lease
        fields = ("project", "status", "payment_frequency")
