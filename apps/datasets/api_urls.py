from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.datasets.views import DatasetRowViewSet, DatasetViewSet

router = DefaultRouter()
router.register("datasets", DatasetViewSet, basename="api-datasets")
router.register("rows", DatasetRowViewSet, basename="api-dataset-rows")
urlpatterns = [path("", include(router.urls))]
