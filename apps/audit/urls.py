from django.urls import path
from apps.audit import views

urlpatterns = [
    path("", views.settings_page, name="settings"),
    path("roles/", views.roles_page, name="roles"),
    path("audit-log/", views.audit_log_page, name="audit_log"),
]
