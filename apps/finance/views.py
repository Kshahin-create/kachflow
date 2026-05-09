from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.shortcuts import render
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects, user_can_view_financials
from apps.finance.models import Account, Category, Transaction
from apps.finance.serializers import AccountSerializer, CategorySerializer, TransactionSerializer


def _project_ids(user):
    return list(get_user_projects(user).values_list("id", flat=True))


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        projects = get_user_projects(self.request.user)
        qs = Account.objects.filter(Q(project__in=projects) | Q(company__projects__in=projects)).distinct()
        if not self.request.user.is_staff:
            allowed_sensitive = [p.id for p in projects if user_can_view_financials(self.request.user, p)]
            qs = qs.filter(Q(is_sensitive=False) | Q(project_id__in=allowed_sensitive))
        return qs


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(project__in=get_user_projects(self.request.user)).select_related("project", "account", "category")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(Q(project__in=get_user_projects(self.request.user)) | Q(project__isnull=True))


@decorators.api_view(["GET"])
def finance_summary(request):
    txns = Transaction.objects.filter(project__in=get_user_projects(request.user))
    income = txns.filter(transaction_type="income").aggregate(total=Sum("amount_base_currency"))["total"] or 0
    expense = txns.filter(transaction_type="expense").aggregate(total=Sum("amount_base_currency"))["total"] or 0
    return response.Response({"income_total": income, "expense_total": expense, "net_cashflow": income - expense})


@login_required
def accounts_page(request):
    accounts = Account.objects.filter(Q(project__in=get_user_projects(request.user)) | Q(company__projects__in=get_user_projects(request.user))).distinct()
    return render(request, "finance/accounts.html", {"accounts": accounts})


@login_required
def transactions_page(request):
    return render(request, "finance/transactions.html", {"transactions": Transaction.objects.filter(project__in=get_user_projects(request.user)).select_related("project", "account")[:100]})


@login_required
def categories_page(request):
    return render(request, "finance/categories.html", {"categories": Category.objects.filter(Q(project__in=get_user_projects(request.user)) | Q(project__isnull=True))})


@login_required
def cashflow_page(request):
    return render(request, "finance/cashflow.html", {})


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TransactionForm

@login_required
def transaction_create_page(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, "تمت إضافة المعاملة بنجاح")
            return redirect("finance_transactions")
    else:
        form = TransactionForm(user=request.user)
    
    return render(request, "finance/transaction_form.html", {"form": form})

@login_required
def transaction_edit_page(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, project__in=get_user_projects(request.user))
    if request.method == "POST":
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث المعاملة بنجاح")
            return redirect("finance_transactions")
    else:
        form = TransactionForm(instance=transaction, user=request.user)
    
    return render(request, "finance/transaction_form.html", {"form": form, "is_edit": True})
