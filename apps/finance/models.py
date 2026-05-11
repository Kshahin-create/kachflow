from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(TimeStampedModel):
    class AccountType(models.TextChoices):
        BANK = "bank", "Bank"
        CASH = "cash", "Cash"
        WALLET = "wallet", "Wallet"
        PAYPAL = "paypal", "PayPal"
        BROKERAGE = "brokerage", "Brokerage"
        PAYMENT_GATEWAY = "payment_gateway", "Payment Gateway"
        OTHER = "other", "Other"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="accounts", blank=True, null=True)
    company = models.ForeignKey("projects.Company", on_delete=models.CASCADE, related_name="accounts", blank=True, null=True)
    name = models.CharField(max_length=180)
    account_type = models.CharField(max_length=32, choices=AccountType.choices, default=AccountType.BANK)
    country = models.CharField(max_length=80, blank=True)
    currency = models.CharField(max_length=8, default="SAR")
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_sensitive = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    class CategoryType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"
        INVESTMENT = "investment", "Investment"
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"

    name = models.CharField(max_length=120)
    type = models.CharField(max_length=24, choices=CategoryType.choices)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="children")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, blank=True, null=True, related_name="categories")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Transaction(TimeStampedModel):
    class TransactionType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"
        INVESTMENT = "investment", "Investment"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        DEPOSIT = "deposit", "Deposit"
        LOAN = "loan", "Loan"
        INSTALLMENT = "installment", "Installment"
        ADJUSTMENT = "adjustment", "Adjustment"

    date = models.DateField()
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="transactions")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=24, choices=TransactionType.choices)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True, related_name="transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="SAR")
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    amount_base_currency = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    customer = models.ForeignKey("ecommerce.Customer", on_delete=models.SET_NULL, blank=True, null=True)
    supplier = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=80, default="manual")
    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.SET_NULL, blank=True, null=True, related_name="transactions")
    attachment = models.FileField(upload_to="transaction_attachments/", blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.amount_base_currency:
            self.amount_base_currency = self.amount * self.exchange_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project} {self.transaction_type} {self.amount}"


class Transfer(models.Model):
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="outgoing_transfers")
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="incoming_transfers")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="SAR")
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class CurrencyRate(models.Model):
    from_currency = models.CharField(max_length=8)
    to_currency = models.CharField(max_length=8)
    rate = models.DecimalField(max_digits=14, decimal_places=6)
    date = models.DateField()
    source = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        unique_together = ("from_currency", "to_currency", "date")
