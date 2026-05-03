import django_filters
from apps.reports.models import Report


class ReportFilter(django_filters.FilterSet):
    class Meta:
        model = Report
        fields = ("project", "report_type", "status")
