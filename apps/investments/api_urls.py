from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.investments.views import AssetViewSet, investments_dashboard_api

router = DefaultRouter()
router.register("assets", AssetViewSet, basename="api-assets")
urlpatterns = [path("", include(router.urls)), path("dashboard/", investments_dashboard_api)]
