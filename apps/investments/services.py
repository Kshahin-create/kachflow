from apps.investments.models import Asset


def create_asset(**data):
    return Asset.objects.create(**data)
