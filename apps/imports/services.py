from decimal import Decimal, InvalidOperation
import pandas as pd
from django.db import transaction
from django.utils import timezone
from apps.datasets.models import Dataset, DatasetField, DatasetRow
from apps.finance.models import Account, Category, Transaction
from apps.imports.models import (
    ImportBatch,
    ImportError,
    RawImportedRow,
    SheetColumn,
    UploadedFile,
    WorkbookSheet,
)


def _json_safe(value):
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value.item() if hasattr(value, "item") else value


def infer_type(values):
    series = pd.Series([v for v in values if pd.notna(v)])
    if series.empty:
        return "text"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    lowered = series.astype(str).str.lower()
    if lowered.isin(["true", "false", "yes", "no", "0", "1"]).mean() > 0.8:
        return "boolean"
    return "text"


def analyze_excel_file(uploaded_file_id, preview_rows=20):
    uploaded = UploadedFile.objects.get(pk=uploaded_file_id)
    uploaded.status = UploadedFile.Status.ANALYZING
    uploaded.save(update_fields=["status"])
    try:
        excel = pd.ExcelFile(uploaded.file.path, engine="openpyxl")
        WorkbookSheet.objects.filter(uploaded_file=uploaded).delete()
        for sheet_name in excel.sheet_names:
            df = excel.parse(sheet_name=sheet_name)
            columns = [str(col).strip() for col in df.columns]
            preview = [
                {str(k): _json_safe(v) for k, v in row.items()}
                for row in df.head(preview_rows).to_dict(orient="records")
            ]
            sheet = WorkbookSheet.objects.create(
                uploaded_file=uploaded,
                sheet_name=sheet_name,
                row_count=len(df.index),
                column_count=len(columns),
                detected_columns=columns,
                preview_data=preview,
            )
            for position, column in enumerate(columns):
                samples = [_json_safe(v) for v in df[column].dropna().head(10).tolist()]
                SheetColumn.objects.create(
                    workbook_sheet=sheet,
                    name=column,
                    detected_type=infer_type(df[column].head(50).tolist()),
                    sample_values=samples,
                    position=position,
                )
        uploaded.status = UploadedFile.Status.ANALYZED
        uploaded.save(update_fields=["status"])
    except Exception as exc:
        uploaded.status = UploadedFile.Status.FAILED
        uploaded.save(update_fields=["status"])
        raise exc
    return uploaded


def _normalize_row(raw_data, mappings):
    normalized = {}
    for mapping in mappings:
        value = raw_data.get(mapping.excel_column, mapping.default_value or None)
        if value in ("", None) and mapping.required:
            raise ValueError(f"Missing required field: {mapping.excel_column}")
        normalized[mapping.system_field] = value
    return normalized


def _decimal(value, default=0):
    try:
        return Decimal(str(value or default).replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _date(value):
    if not value:
        return timezone.localdate()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return timezone.localdate()
    return parsed.date()


def _import_transaction(batch, normalized, raw_row):
    account_name = normalized.get("account") or normalized.get("account_name") or "Default"
    account, _ = Account.objects.get_or_create(
        project=batch.project,
        name=account_name,
        defaults={"currency": batch.project.base_currency, "current_balance": 0},
    )
    category = None
    if normalized.get("category"):
        category, _ = Category.objects.get_or_create(
            project=batch.project,
            name=normalized["category"],
            defaults={"type": normalized.get("transaction_type") or "expense"},
        )
    txn = Transaction.objects.create(
        date=_date(normalized.get("date")),
        project=batch.project,
        account=account,
        transaction_type=normalized.get("transaction_type") or "expense",
        category=category,
        amount=_decimal(normalized.get("amount")),
        currency=normalized.get("currency") or batch.project.base_currency,
        exchange_rate=_decimal(normalized.get("exchange_rate"), 1),
        description=normalized.get("description") or "",
        source="excel",
        import_batch=batch,
        created_by=batch.created_by,
    )
    raw_row.target_model = "finance.Transaction"
    raw_row.target_object_id = str(txn.pk)
    raw_row.save(update_fields=["target_model", "target_object_id"])


def _import_dataset(batch, normalized, raw_row):
    dataset, _ = Dataset.objects.get_or_create(
        project=batch.project,
        name=f"{batch.template.name} - {batch.template.sheet_name}",
        source_type="excel",
        source_file=batch.uploaded_file,
        sheet_name=batch.template.sheet_name,
        defaults={"created_by": batch.created_by},
    )
    for position, key in enumerate(raw_row.raw_data.keys()):
        DatasetField.objects.get_or_create(
            dataset=dataset,
            name=key,
            defaults={"position": position, "sample_values": [raw_row.raw_data.get(key)]},
        )
    row = DatasetRow.objects.create(
        dataset=dataset,
        raw_data=raw_row.raw_data,
        normalized_data=normalized,
        import_batch=batch,
        row_number=raw_row.row_number,
    )
    raw_row.target_model = "datasets.DatasetRow"
    raw_row.target_object_id = str(row.pk)
    raw_row.save(update_fields=["target_model", "target_object_id"])


@transaction.atomic
def run_import_batch(batch_id):
    batch = ImportBatch.objects.select_related("template", "uploaded_file", "project").get(pk=batch_id)
    batch.status = ImportBatch.Status.RUNNING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at"])
    mappings = list(batch.template.mappings.all())
    df = pd.read_excel(batch.uploaded_file.file.path, sheet_name=batch.template.sheet_name, engine="openpyxl")
    batch.total_rows = len(df.index)
    imported = failed = 0
    for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
        raw_data = {str(k): _json_safe(v) for k, v in row.items()}
        raw_row = RawImportedRow.objects.create(
            project=batch.project,
            batch=batch,
            sheet_name=batch.template.sheet_name,
            row_number=row_number,
            raw_data=raw_data,
        )
        try:
            normalized = _normalize_row(raw_data, mappings)
            raw_row.normalized_data = normalized
            raw_row.save(update_fields=["normalized_data"])
            if batch.template.target_type == "transactions":
                _import_transaction(batch, normalized, raw_row)
            else:
                _import_dataset(batch, normalized, raw_row)
            imported += 1
        except Exception as exc:
            failed += 1
            raw_row.status = RawImportedRow.Status.FAILED
            raw_row.error_message = str(exc)
            raw_row.save(update_fields=["status", "error_message"])
            ImportError.objects.create(batch=batch, row_number=row_number, error_message=str(exc), raw_data=raw_data)
    batch.imported_rows = imported
    batch.failed_rows = failed
    batch.status = ImportBatch.Status.COMPLETED if failed == 0 else ImportBatch.Status.FAILED
    batch.finished_at = timezone.now()
    batch.save(update_fields=["total_rows", "imported_rows", "failed_rows", "status", "finished_at"])
    return batch


@transaction.atomic
def rollback_import_batch(batch_id):
    batch = ImportBatch.objects.get(pk=batch_id)
    for raw in batch.raw_rows.exclude(target_model="", target_object_id=""):
        if raw.target_model == "finance.Transaction":
            Transaction.objects.filter(pk=raw.target_object_id, import_batch=batch).delete()
        if raw.target_model == "datasets.DatasetRow":
            DatasetRow.objects.filter(pk=raw.target_object_id, import_batch=batch).delete()
        raw.status = RawImportedRow.Status.ROLLED_BACK
        raw.save(update_fields=["status"])
    batch.status = ImportBatch.Status.ROLLED_BACK
    batch.save(update_fields=["status"])
    return batch
