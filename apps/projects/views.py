from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets, decorators, response, status
from apps.accounts.models import ProjectMember, ProjectInvitation
from apps.accounts.selectors import get_user_projects, user_can_access_project, user_can_manage_project_users
from apps.audit.services import log_action
from apps.dashboards.services import get_partner_dashboard_metrics, get_project_dashboard_metrics
from apps.projects.models import Company, Project
from apps.projects.serializers import CompanySerializer, ProjectMemberSerializer, ProjectSerializer, ProjectInvitationSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Company.objects.all()
        return Company.objects.filter(projects__in=get_user_projects(self.request.user)).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return get_user_projects(self.request.user)

    @decorators.action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        project = self.get_object()
        metrics = get_project_dashboard_metrics(request.user, project.pk).copy()
        metrics["project"] = {"id": project.pk, "name": project.name, "project_type": project.project_type}
        metrics.pop("recent_imports", None)
        metrics.pop("recent_transactions", None)
        return response.Response(metrics)

    @decorators.action(detail=True, methods=["get"], url_path="partner-dashboard")
    def partner_dashboard(self, request, pk=None):
        project = self.get_object()
        data = get_partner_dashboard_metrics(request.user, project.pk)
        if data.get("forbidden"):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data["project"] = {"id": project.pk, "name": project.name, "project_type": project.project_type}
        return response.Response(data)

    @decorators.action(detail=True, methods=["get"], url_path="permissions/me")
    def my_permissions(self, request, pk=None):
        project = self.get_object()
        membership = ProjectMember.objects.filter(project=project, user=request.user, is_active=True).first()
        return response.Response(ProjectMemberSerializer(membership).data if membership else {"role": "owner" if request.user.is_staff else "none"})


class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(project__in=get_user_projects(self.request.user))


class ProjectInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectInvitationSerializer

    def get_queryset(self):
        return ProjectInvitation.objects.filter(project__in=get_user_projects(self.request.user))

    def perform_create(self, serializer):
        invitation = serializer.save(invited_by=self.request.user)
        log_action(self.request.user, invitation.project, "invite_user", invitation, f"Invited {invitation.email}", request=self.request)


@login_required
def project_list(request):
    return render(request, "projects/list.html", {"projects": get_user_projects(request.user)})


def _project_entry_url(project):
    if project.project_type in [Project.ProjectType.REAL_ESTATE, Project.ProjectType.LEASING]:
        return "real_estate_dashboard"
    if project.project_type == Project.ProjectType.ECOMMERCE:
        return "ecommerce_dashboard"
    if project.project_type == Project.ProjectType.ADS:
        return "ads_dashboard"
    if project.project_type == Project.ProjectType.INVESTMENT:
        return "investments_dashboard"
    return "project_dashboard"


@login_required
def project_select(request):
    projects = get_user_projects(request.user)
    if request.method == "POST":
        project = get_object_or_404(projects, pk=request.POST.get("project"))
        request.session["current_project_id"] = project.pk
        request.session.modified = True
        target = _project_entry_url(project)
        if target == "project_dashboard":
            return redirect(target, pk=project.pk)
        return redirect(target)
    return render(request, "projects/select.html", {"projects": projects})


@login_required
def project_switch(request, pk):
    project = get_object_or_404(get_user_projects(request.user), pk=pk)
    request.session["current_project_id"] = project.pk
    request.session.modified = True
    target = _project_entry_url(project)
    if target == "project_dashboard":
        return redirect(target, pk=project.pk)
    return redirect(target)


@login_required
def project_create(request):
    companies = Company.objects.filter(owner=request.user) if not request.user.is_staff else Company.objects.all()
    if request.method == "POST":
        company_id = request.POST.get("company")
        company = Company.objects.filter(pk=company_id).first() or Company.objects.create(name=request.POST.get("company_name") or "Default Company", owner=request.user)
        project = Project.objects.create(
            company=company,
            name=request.POST["name"],
            project_type=request.POST.get("project_type", "generic"),
            base_currency=request.POST.get("base_currency", "SAR"),
            country=request.POST.get("country", ""),
        )
        ProjectMember.objects.get_or_create(
            user=request.user,
            project=project,
            defaults={"role": "owner", "dashboard_access": "full", "can_view_dashboard": True, "can_view_financials": True, "can_manage_users": True, "can_upload_excel": True, "can_import_data": True},
        )
        log_action(request.user, project, "create_project", project, request=request)
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"companies": companies})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_access_project(request.user, project):
        raise PermissionDenied
    return render(request, "projects/detail.html", {"project": project})


@login_required
def project_dashboard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_access_project(request.user, project):
        raise PermissionDenied
    return render(request, "projects/dashboard.html", {"metrics": get_project_dashboard_metrics(request.user, pk), "project": project})


@login_required
def partner_dashboard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = get_partner_dashboard_metrics(request.user, pk)
    if data.get("forbidden"):
        raise PermissionDenied
    return render(request, "projects/partner_dashboard.html", {"metrics": data, "project": project})


@login_required
def project_members(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_manage_project_users(request.user, project):
        raise PermissionDenied
    return render(request, "projects/members.html", {"project": project, "members": project.members.select_related("user")})


@login_required
def member_permissions(request, pk, member_id):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_manage_project_users(request.user, project):
        raise PermissionDenied
    member = get_object_or_404(ProjectMember, pk=member_id, project=project)
    if request.method == "POST":
        bool_fields = [f.name for f in ProjectMember._meta.fields if f.name.startswith("can_")]
        for field in bool_fields:
            setattr(member, field, request.POST.get(field) == "on")
        member.role = request.POST.get("role", member.role)
        member.dashboard_access = request.POST.get("dashboard_access", member.dashboard_access)
        member.save()
        messages.success(request, "تم تحديث الصلاحيات.")
        log_action(request.user, project, "update_permissions", member, request=request)
        return redirect("project_members", pk=project.pk)
    return render(request, "projects/member_permissions.html", {"project": project, "member": member})
