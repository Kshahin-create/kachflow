from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.accounts.models import ProjectMember
from apps.dashboards.services import get_global_dashboard_metrics
from apps.finance.models import Account, Transaction
from apps.projects.models import Company, Project
from datetime import date


class DashboardMetricTests(TestCase):
    def test_dashboard_metrics_are_project_scoped(self):
        user = get_user_model().objects.create_user("owner", password="pw")
        company = Company.objects.create(name="Demo", owner=user)
        project = Project.objects.create(company=company, name="Scoped")
        ProjectMember.objects.create(user=user, project=project, can_view_dashboard=True, can_view_financials=True)
        account = Account.objects.create(project=project, name="Bank", current_balance=1000)
        Transaction.objects.create(project=project, account=account, date=date.today(), transaction_type="income", amount=250, amount_base_currency=250)
        metrics = get_global_dashboard_metrics(user)
        self.assertEqual(metrics["income_total"], 250.0)
        self.assertEqual(metrics["cash_total"], 1000.0)
