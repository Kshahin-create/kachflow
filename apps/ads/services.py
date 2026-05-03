from apps.ads.models import AdSpendDaily


def create_ad_spend(**data):
    return AdSpendDaily.objects.create(**data)
