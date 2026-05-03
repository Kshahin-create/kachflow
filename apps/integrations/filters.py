import django_filters
from apps.integrations.models import ApiConnection


class ApiConnectionFilter(django_filters.FilterSet):
    class Meta:
        model = ApiConnection
        fields = ("project", "provider", "status")
