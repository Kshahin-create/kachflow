from apps.real_estate.models import Lease


def create_lease(**data):
    return Lease.objects.create(**data)
