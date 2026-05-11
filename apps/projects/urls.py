from django.urls import path
from apps.projects import views

urlpatterns = [
    path("select/", views.project_select, name="project_select"),
    path("switch/<int:pk>/", views.project_switch, name="project_switch"),
    path("", views.project_list, name="project_list"),
    path("create/", views.project_create, name="project_create"),
    path("<int:pk>/", views.project_detail, name="project_detail"),
    path("<int:pk>/edit/", views.project_create, name="project_edit"),
    path("<int:pk>/settings/", views.project_detail, name="project_settings"),
    path("<int:pk>/dashboard/", views.project_dashboard, name="project_dashboard"),
    path("<int:pk>/analytics/", views.project_analytics, name="project_analytics"),
    path("<int:pk>/partner-dashboard/", views.partner_dashboard, name="partner_dashboard"),
    path("<int:pk>/members/", views.project_members, name="project_members"),
    path("<int:pk>/members/<int:member_id>/permissions/", views.member_permissions, name="member_permissions"),
]
