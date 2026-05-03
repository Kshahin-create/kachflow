from rest_framework import serializers
from apps.datasets.models import Dataset, DatasetField, DatasetRow


class DatasetFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetField
        fields = "__all__"


class DatasetRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetRow
        fields = "__all__"


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = "__all__"
