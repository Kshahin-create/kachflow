from apps.reports.models import Report


def create_report(**data):
    return Report.objects.create(**data)
