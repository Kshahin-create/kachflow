from apps.integrations.models import SyncLog


def log_sync(api_connection, status, **metadata):
    return SyncLog.objects.create(api_connection=api_connection, status=status, **metadata)
