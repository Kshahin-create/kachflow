from django.contrib import admin
from apps.ecommerce.models import Customer, Order, OrderItem, Product, Refund, ShippingCost


admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Refund)
admin.site.register(ShippingCost)
