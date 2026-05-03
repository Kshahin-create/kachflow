from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.imports.views import ImportBatchViewSet, ImportTemplateViewSet, UploadedFileViewSet

router = DefaultRouter()
router.register("upload", UploadedFileViewSet, basename="api-import-upload")
router.register("templates", ImportTemplateViewSet, basename="api-import-templates")
router.register("batches", ImportBatchViewSet, basename="api-import-batches")

urlpatterns = [path("", include(router.urls))]
