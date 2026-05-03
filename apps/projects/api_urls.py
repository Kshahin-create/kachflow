from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.projects.views import CompanyViewSet, ProjectInvitationViewSet, ProjectMemberViewSet, ProjectViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="api-companies")
router.register("members", ProjectMemberViewSet, basename="api-project-members")
router.register("invitations", ProjectInvitationViewSet, basename="api-project-invitations")
router.register("", ProjectViewSet, basename="api-projects")

urlpatterns = [path("", include(router.urls))]
