from django.db.models import Sum, Count, Q
from apps.accounts.selectors import get_user_projects, user_can_view_financials, user_can_view_partner_dashboard
from apps.finance.models import Account, Transaction
from apps.imports.models import UploadedFile
from apps.projects.models import Project
from apps.accounts.models import ProjectStakeholder


def _money(value):
    return float(value or 0)


def get_finance_metrics(user, project_id=None):
    projects = get_user_projects(user)
    if project_id:
        projects = projects.filter(pk=project_id)
    accounts = Account.objects.filter(Q(project__in=projects) | Q(company__projects__in=projects)).distinct()
    transactions = Transaction.objects.filter(project__in=projects)
    income = transactions.filter(transaction_type__in=["income", "deposit"]).aggregate(total=Sum("amount_base_currency"))["total"]
    expense = transactions.filter(transaction_type__in=["expense", "withdrawal"]).aggregate(total=Sum("amount_base_currency"))["total"]
    return {
        "cash_total": _money(accounts.aggregate(total=Sum("current_balance"))["total"]),
        "income_total": _money(income),
        "expense_total": _money(expense),
        "net_cashflow": _money(income) - _money(expense),
        "accounts_count": accounts.count(),
        "transactions_count": transactions.count(),
    }


def get_global_dashboard_metrics(user):
    projects = get_user_projects(user)
    metrics = get_finance_metrics(user)
    metrics.update({
        "projects_count": projects.count(),
        "recent_uploads": UploadedFile.objects.filter(project__in=projects).select_related("project").order_by("-uploaded_at")[:5],
        "recent_transactions": Transaction.objects.filter(project__in=projects).select_related("project", "account").order_by("-created_at")[:5],
        "project_profitability": [
            {"name": p.name, "income": _money(Transaction.objects.filter(project=p, transaction_type="income").aggregate(total=Sum("amount_base_currency"))["total"])}
            for p in projects[:8]
        ],
    })
    return metrics


def get_project_dashboard_metrics(user, project_id):
    project = Project.objects.get(pk=project_id)
    if not user_can_view_financials(user, project):
        return {"project": project, "limited": True}
    metrics = get_finance_metrics(user, project_id=project_id)
    metrics["project"] = project
    metrics["recent_imports"] = project.import_batches.order_by("-created_at")[:5]
    metrics["recent_transactions"] = project.transactions.select_related("account").order_by("-created_at")[:8]
    return metrics


def get_partner_dashboard_metrics(user, project_id):
    project = Project.objects.get(pk=project_id)
    if not user_can_view_partner_dashboard(user, project):
        return {"project": project, "forbidden": True}
    metrics = get_finance_metrics(user, project_id=project_id)
    stake = ProjectStakeholder.objects.filter(project=project, user=user).first()
    profit_share = float(stake.profit_share_percentage if stake else 0)
    net_profit = metrics["income_total"] - metrics["expense_total"]
    return {
        "project": project,
        "income_total": metrics["income_total"],
        "expense_total": metrics["expense_total"],
        "net_profit": net_profit,
        "roi": 0,
        "ownership_percentage": float(stake.ownership_percentage if stake else 0),
        "profit_share": profit_share,
        "partner_profit": net_profit * profit_share / 100,
        "status": project.status,
    }


def get_ecommerce_metrics(user, project_id):
    return get_project_dashboard_metrics(user, project_id)


def get_real_estate_metrics(user, project_id):
    return get_project_dashboard_metrics(user, project_id)


def get_ads_metrics(user, project_id):
    return get_project_dashboard_metrics(user, project_id)


def get_investment_metrics(user, project_id=None):
    return get_finance_metrics(user, project_id)
