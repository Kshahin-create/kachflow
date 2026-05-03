from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.accounts.views import UserViewSet

router = DefaultRouter()
router.register("", UserViewSet, basename="api-users")
urlpatterns = [path("", include(router.urls))]
