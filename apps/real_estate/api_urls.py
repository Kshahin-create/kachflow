from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.real_estate.views import CollectionViewSet, LeaseViewSet, PropertyViewSet, real_estate_dashboard_api

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="api-properties")
router.register("leases", LeaseViewSet, basename="api-leases")
router.register("collections", CollectionViewSet, basename="api-collections")
urlpatterns = [path("", include(router.urls)), path("dashboard/", real_estate_dashboard_api)]
