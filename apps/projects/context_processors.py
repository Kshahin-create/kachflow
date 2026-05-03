from apps.accounts.selectors import get_user_projects


def accessible_projects(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"accessible_projects": [], "current_project": None}
    projects = get_user_projects(request.user)
    current_project = None
    current_project_id = request.session.get("current_project_id")
    if current_project_id:
        current_project = projects.filter(pk=current_project_id).first()
    return {"accessible_projects": projects[:20], "current_project": current_project}
