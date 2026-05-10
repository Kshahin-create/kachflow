from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_global_dashboard_metrics


@login_required
def dashboard_home(request):
    project_id = request.session.get("current_project_id")
    projects = get_user_projects(request.user)
    if not project_id or not projects.filter(pk=project_id).exists():
        return redirect("project_select")
    return render(request, "dashboard/home.html", {"metrics": get_global_dashboard_metrics(request.user, projects=projects)})
