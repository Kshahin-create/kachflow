from django.db import models


class Customer(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="customers")
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    name = models.CharField(max_length=180)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    addresses_json = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    tags_json = models.JSONField(default=list, blank=True)
    first_order_date = models.DateField(blank=True, null=True)
    last_order_date = models.DateField(blank=True, null=True)
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PromoCode(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="promo_codes")
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    code = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    promo_type = models.CharField(max_length=60, blank=True) # PERCENTAGE_OFF, FIXED_AMOUNT
    status = models.CharField(max_length=40, default="ACTIVE")
    percentage_off = models.FloatField(default=0)
    fixed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    usage_limit = models.IntegerField(default=0)
    number_of_usage = models.IntegerField(default=0)
    is_archived = models.BooleanField(default=False)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class ProductCollection(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="collections")
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    title = models.CharField(max_length=180)
    handle = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    products_count = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Product(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="products")
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    handle = models.CharField(max_length=180, blank=True)
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=180)
    category = models.CharField(max_length=120, blank=True)
    collections = models.ManyToManyField(ProductCollection, blank=True, related_name="products")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=40, default="ACTIVE")
    product_type = models.CharField(max_length=80, blank=True)
    tags = models.JSONField(default=list, blank=True)
    images_json = models.JSONField(default=list, blank=True)
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    compare_at_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="SAR")
    stock_quantity = models.IntegerField(default=0)
    variants_json = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def profit_margin(self):
        return self.selling_price - self.cost_price

    def __str__(self):
        return self.name


class Order(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="orders")
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    order_number = models.CharField(max_length=120)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name="orders")
    order_date = models.DateField()
    status = models.CharField(max_length=60, blank=True)
    fulfillment_status = models.CharField(max_length=60, blank=True)
    payment_status = models.CharField(max_length=60, blank=True)
    shipping_status = models.CharField(max_length=60, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    tracking_url = models.URLField(blank=True, max_length=500)
    payment_method = models.CharField(max_length=120, blank=True)
    payment_intent_id = models.CharField(max_length=160, blank=True)
    shipping_address_json = models.JSONField(default=dict, blank=True)
    packaging_details_json = models.JSONField(default=dict, blank=True)
    tags_json = models.JSONField(default=list, blank=True)
    is_viewed = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_abandoned = models.BooleanField(default=False) # New field
    gross_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="SAR")
    source = models.CharField(max_length=80, default="manual")
    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.SET_NULL, blank=True, null=True)
    raw_data = models.JSONField(default=dict, blank=True)
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
