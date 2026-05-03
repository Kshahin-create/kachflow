from apps.accounts.models import ProjectInvitation, ProjectMember


def invite_project_user(*, project, email, role, invited_by, dashboard_access="readonly"):
    return ProjectInvitation.objects.create(project=project, email=email, role=role, dashboard_access=dashboard_access, invited_by=invited_by)


def set_project_member_permissions(member: ProjectMember, **flags):
    for key, value in flags.items():
        if hasattr(member, key):
            setattr(member, key, value)
    member.save()
    return member
