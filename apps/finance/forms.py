from django import forms
from django.db.models import Q
from apps.finance.models import Transaction, Account, Category
from apps.projects.models import Project

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'project', 'account', 'category', 'transaction_type', 'amount', 'currency', 'description', 'supplier']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'supplier': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from apps.accounts.selectors import get_user_projects
            projects = get_user_projects(user)
            self.fields['project'].queryset = projects
            self.fields['account'].queryset = Account.objects.filter(project__in=projects)
            self.fields['category'].queryset = Category.objects.filter(
                Q(project__in=projects) | Q(project__isnull=True)
            )
