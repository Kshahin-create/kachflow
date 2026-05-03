from config.celery import app
from apps.imports.services import analyze_excel_file, rollback_import_batch, run_import_batch


@app.task
def analyze_excel_file_task(file_id):
    return analyze_excel_file(file_id).pk


@app.task
def run_import_batch_task(batch_id):
    return run_import_batch(batch_id).pk


@app.task
def rollback_import_batch_task(batch_id):
    return rollback_import_batch(batch_id).pk
