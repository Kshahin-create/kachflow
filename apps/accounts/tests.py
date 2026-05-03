from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.accounts.models import ProjectMember
from apps.accounts.selectors import get_user_projects, user_can_access_project
from apps.projects.models import Company, Project


class ProjectPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pw")
        self.viewer = User.objects.create_user("viewer", password="pw")
        self.outsider = User.objects.create_user("outsider", password="pw")
        self.company = Company.objects.create(name="Demo", owner=self.owner)
        self.project = Project.objects.create(company=self.company, name="Demo Project")
        ProjectMember.objects.create(user=self.viewer, project=self.project, role="viewer", can_view_dashboard=True)

    def test_user_projects_are_scoped_to_membership(self):
        self.assertIn(self.project, get_user_projects(self.viewer))
        self.assertNotIn(self.project, get_user_projects(self.outsider))

    def test_user_can_access_project_only_with_membership(self):
        self.assertTrue(user_can_access_project(self.viewer, self.project))
        self.assertFalse(user_can_access_project(self.outsider, self.project))
