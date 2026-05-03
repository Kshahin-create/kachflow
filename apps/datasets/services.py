from apps.datasets.models import DatasetRow


def create_dataset_row(dataset, raw_data, row_number, normalized_data=None, import_batch=None):
    return DatasetRow.objects.create(dataset=dataset, raw_data=raw_data, normalized_data=normalized_data or {}, row_number=row_number, import_batch=import_batch)
