from apps.accounts.selectors import get_user_projects
from apps.imports.models import UploadedFile


def list_uploaded_files_for_user(user):
    return UploadedFile.objects.filter(project__in=get_user_projects(user))
