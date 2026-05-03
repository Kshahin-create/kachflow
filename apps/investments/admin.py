from django.contrib import admin
from apps.investments.models import Asset, InvestmentIncome, InvestmentTransaction


admin.site.register(Asset)
admin.site.register(InvestmentTransaction)
admin.site.register(InvestmentIncome)
