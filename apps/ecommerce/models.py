from django.db import models


class Customer(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    first_order_date = models.DateField(blank=True, null=True)
    last_order_date = models.DateField(blank=True, null=True)
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="products")
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=180)
    category = models.CharField(max_length=120, blank=True)
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="SAR")
    stock_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=120)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name="orders")
    order_date = models.DateField()
    status = models.CharField(max_length=60, blank=True)
    gross_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="SAR")
    source = models.CharField(max_length=80, default="manual")
    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    product_name = models.CharField(max_length=180)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    date = models.DateField()


class ShippingCost(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipping_costs")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    provider = models.CharField(max_length=120, blank=True)
    date = models.DateField()
