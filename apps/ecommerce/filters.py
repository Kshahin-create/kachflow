import django_filters
from apps.ecommerce.models import Order


class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = Order
        fields = ("project", "status", "source")
