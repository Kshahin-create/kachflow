from django.urls import path
from apps.imports import views

urlpatterns = [
    path("upload/", views.upload_page, name="import_upload"),
    path("<int:file_id>/sheets/", views.sheets_page, name="import_sheets"),
    path("<int:file_id>/preview/<str:sheet_name>/", views.preview_page, name="import_preview"),
    path("<int:file_id>/mapping/<str:sheet_name>/", views.mapping_page, name="import_mapping"),
    path("batches/", views.batches_page, name="import_batches"),
    path("templates/", views.templates_page, name="import_templates"),
]
