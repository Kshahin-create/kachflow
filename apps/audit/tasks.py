from config.celery import app
from apps.audit.services import create_database_backup


@app.task
def create_backup_task(label="نسخة احتياطية تلقائية"):
    backup = create_database_backup(created_by=None, label=label)
    return backup.pk
