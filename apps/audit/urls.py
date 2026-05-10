from django.urls import path
from apps.audit import views

urlpatterns = [
    path("", views.settings_page, name="settings"),
    path("backups/", views.backups_page, name="backups_page"),
    path("restore/", views.restore_page, name="restore_page"),
    path("backups/<int:backup_id>/download/", views.backup_download, name="backup_download"),
    path("roles/", views.roles_page, name="roles"),
    path("audit-log/", views.audit_log_page, name="audit_log"),
]
