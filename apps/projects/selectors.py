from apps.accounts.selectors import get_user_projects


def list_projects_for_user(user):
    return get_user_projects(user)
