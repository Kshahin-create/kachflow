from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_ecommerce_metrics
from apps.ecommerce.models import Customer, Order, Product
from apps.ecommerce.serializers import CustomerSerializer, OrderSerializer, ProductSerializer


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer
    def get_queryset(self):
        return Customer.objects.filter(project__in=get_user_projects(self.request.user))


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    def get_queryset(self):
        return Product.objects.filter(project__in=get_user_projects(self.request.user))


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    def get_queryset(self):
        return Order.objects.filter(project__in=get_user_projects(self.request.user))


@decorators.api_view(["GET"])
def ecommerce_dashboard_api(request):
    project_id = request.query_params.get("project")
    return response.Response(get_ecommerce_metrics(request.user, project_id) if project_id else {})


@login_required
def dashboard_page(request):
    return render(request, "ecommerce/dashboard.html", {})


@login_required
def orders_page(request):
    return render(request, "ecommerce/orders.html", {"orders": Order.objects.filter(project__in=get_user_projects(request.user))[:100]})


@login_required
def products_page(request):
    return render(request, "ecommerce/products.html", {"products": Product.objects.filter(project__in=get_user_projects(request.user))[:100]})


@login_required
def customers_page(request):
    return render(request, "ecommerce/customers.html", {"customers": Customer.objects.filter(project__in=get_user_projects(request.user))[:100]})
