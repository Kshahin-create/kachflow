import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.core.cache import cache
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from rest_framework import viewsets, decorators, response
from datetime import timedelta
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_ecommerce_metrics
from apps.ecommerce.models import Customer, Order, Product, ProductCollection, PromoCode
from apps.ecommerce.serializers import CustomerSerializer, OrderSerializer, ProductSerializer
from apps.integrations.models import ApiConnection, RawApiEvent
from common.utils import resolve_period, get_project_version, get_user_version
from apps.integrations.wuilt import (
    DEFAULT_GRAPHQL_ENDPOINT,
    WUILT_PROVIDER,
    WuiltApiClient,
    masked_key,
    process_wuilt_webhook,
    sync_wuilt_connection,
)


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
    project = _selected_project(request)
    if not project:
        return render(request, "ecommerce/dashboard.html", {"empty_project": True})
    return render(request, "ecommerce/dashboard.html", {
        "project": project,
        "load_charts": True,
        "products_count": Product.objects.filter(project=project).count(),
        "orders_count": Order.objects.filter(project=project).count(),
        "customers_count": Customer.objects.filter(project=project).count(),
        "api_connection": _wuilt_connection(project),
    })


@login_required
def dashboard(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    
    from django.db.models import Sum, Count, Q, Avg
    from django.utils import timezone

    period_ctx = resolve_period(request, default="14d")
    
    # Basic Stats
    error_message = ""
    paid_statuses = ["SUCCESSFUL", "PAID", "COMPLETED", "successful", "paid"]
    user_ver = get_user_version(request.user)
    project_ver = get_project_version(project.pk)
    cache_key = f"ecom:dash:{request.user.pk}:{project.pk}:{period_ctx['start']}:{period_ctx['end']}:{user_ver}:{project_ver}"
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, "ecommerce/dashboard.html", cached)

    orders = Order.objects.filter(project=project, order_date__range=[period_ctx["start"], period_ctx["end"]])
    try:
        stats = orders.aggregate(
            total_sales=Sum("net_total", filter=Q(status__in=paid_statuses)),
            total_orders=Count("id"),
            abandoned_count=Count("id", filter=Q(is_abandoned=True)),
            customers_count=Count("customer", distinct=True),
            avg_order_value=Avg("net_total", filter=Q(status__in=paid_statuses)),
        )
    except Exception as exc:
        error_message = f"فشل حساب إحصائيات المتجر: {exc}"
        stats = {"total_sales": 0, "total_orders": 0, "abandoned_count": 0, "customers_count": 0, "avg_order_value": 0}

    prev_orders = Order.objects.filter(project=project, order_date__range=[period_ctx["prev_start"], period_ctx["prev_end"]])
    try:
        prev_stats = prev_orders.aggregate(
            total_sales=Sum("net_total", filter=Q(status__in=paid_statuses)),
            total_orders=Count("id"),
            abandoned_count=Count("id", filter=Q(is_abandoned=True)),
            customers_count=Count("customer", distinct=True),
            avg_order_value=Avg("net_total", filter=Q(status__in=paid_statuses)),
        )
    except Exception:
        prev_stats = {"total_sales": 0, "total_orders": 0, "abandoned_count": 0, "customers_count": 0, "avg_order_value": 0}

    def _pct_change(curr, prev):
        try:
            c = float(curr or 0)
            p = float(prev or 0)
            if p == 0:
                return None
            return round(((c - p) / p) * 100, 1)
        except Exception:
            return None

    compare = {
        "sales_pct": _pct_change(stats.get("total_sales"), prev_stats.get("total_sales")),
        "orders_pct": _pct_change(stats.get("total_orders"), prev_stats.get("total_orders")),
        "aov_pct": _pct_change(stats.get("avg_order_value"), prev_stats.get("avg_order_value")),
        "abandoned_pct": _pct_change(stats.get("abandoned_count"), prev_stats.get("abandoned_count")),
    }
    
    # Sales Chart Data (by selected period)
    sales_data = []
    try:
        sales_data = (
            orders.filter(status__in=paid_statuses)
            .values("order_date")
            .annotate(daily_total=Sum("net_total"), daily_count=Count("id"))
            .order_by("order_date")
        )
    except Exception as exc:
        if not error_message:
            error_message = f"فشل تجهيز بيانات الرسم البياني: {exc}"

    # Format chart labels and values
    chart_labels = []
    chart_sales = []
    chart_counts = []
    
    try:
        curr_date = period_ctx["start"]
        sales_dict = {item["order_date"]: item for item in sales_data}
        while curr_date <= period_ctx["end"]:
            chart_labels.append(curr_date.strftime("%m/%d"))
            item = sales_dict.get(curr_date)
            chart_sales.append(float(item["daily_total"]) if item and item["daily_total"] else 0)
            chart_counts.append(int(item["daily_count"]) if item and item["daily_count"] else 0)
            curr_date += timedelta(days=1)
    except Exception as exc:
        if not error_message:
            error_message = f"فشل تجهيز الرسم البياني: {exc}"
    
    # Recent Activity
    recent_orders = orders.order_by("-order_date", "-created_at")[:5]
    top_products = Product.objects.filter(project=project).order_by("-stock_quantity")[:5]
    
    context = {
        "project": project,
        "load_charts": True,
        "period_ctx": period_ctx,
        "error_message": error_message,
        "stats": stats,
        "prev_stats": prev_stats,
        "compare": compare,
        "recent_orders": recent_orders,
        "top_products": top_products,
        "chart_labels": json.dumps(chart_labels),
        "chart_sales": json.dumps(chart_sales),
        "chart_counts": json.dumps(chart_counts),
    }
    cache.set(cache_key, context, 30)
    return render(request, "ecommerce/dashboard.html", context)


@login_required
def orders_page(request):
    project = _selected_project(request)
    if project and request.GET.get("sync") == "1":
        connection = _wuilt_connection(project)
        if connection:
            try:
                sync_log = sync_wuilt_connection(connection)
                messages.success(request, f"تمت المزامنة بنجاح: تم سحب {sync_log.records_fetched} سجل.")
            except Exception as exc:
                messages.error(request, f"فشلت المزامنة: {exc}")
        else:
            messages.warning(request, "لم يتم العثور على اتصال Wuilt لهذا المشروع.")
        return redirect("ecommerce_orders")

    abandoned = request.GET.get("abandoned") == "1"
    orders_qs = Order.objects.filter(project=project, is_abandoned=abandoned).select_related("customer").order_by("-order_date", "-created_at") if project else Order.objects.none()
    paginator = Paginator(orders_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    qs = request.GET.copy()
    qs.pop("page", None)
    return render(request, "ecommerce/orders.html", {
        "project": project,
        "orders": page_obj.object_list,
        "page_obj": page_obj,
        "qs": qs.urlencode(),
        "is_abandoned_view": abandoned,
    })


@login_required
def order_detail(request, order_id):
    project = _selected_project(request)
    from django.shortcuts import get_object_or_404
    order = get_object_or_404(Order, pk=order_id, project__in=get_user_projects(request.user))
    return render(request, "ecommerce/order_detail.html", {
        "project": project,
        "order": order,
        "items": order.items.all(),
    })


@login_required
def products_page(request):
    project = _selected_project(request)
    if project and request.GET.get("sync") == "1":
        connection = _wuilt_connection(project)
        if connection:
            try:
                sync_log = sync_wuilt_connection(connection)
                messages.success(request, f"تمت المزامنة بنجاح.")
            except Exception as exc:
                messages.error(request, f"فشلت المزامنة: {exc}")
        return redirect("ecommerce_products")

    products_qs = Product.objects.filter(project=project).order_by("-created_at") if project else Product.objects.none()
    paginator = Paginator(products_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    qs = request.GET.copy()
    qs.pop("page", None)
    return render(request, "ecommerce/products.html", {"project": project, "products": page_obj.object_list, "page_obj": page_obj, "qs": qs.urlencode()})


@login_required
def product_detail(request, product_id):
    project = _selected_project(request)
    from django.shortcuts import get_object_or_404
    product = get_object_or_404(Product, pk=product_id, project__in=get_user_projects(request.user))
    return render(request, "ecommerce/product_detail.html", {
        "project": project,
        "product": product,
    })


@login_required
def customers_page(request):
    project = _selected_project(request)
    customers_qs = Customer.objects.filter(project=project).order_by("-created_at") if project else Customer.objects.none()
    paginator = Paginator(customers_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    qs = request.GET.copy()
    qs.pop("page", None)
    return render(request, "ecommerce/customers.html", {"project": project, "customers": page_obj.object_list, "page_obj": page_obj, "qs": qs.urlencode()})


@login_required
def customer_detail(request, customer_id):
    project = _selected_project(request)
    from django.shortcuts import get_object_or_404
    from django.db.models import Avg, Sum
    
    customer = get_object_or_404(Customer, pk=customer_id, project__in=get_user_projects(request.user))
    orders = customer.orders.all().order_by("-order_date", "-created_at")
    
    # Calculate stats if not synced/updated recently
    stats = orders.aggregate(
        total_spent=Sum("net_total"),
        avg_order=Avg("net_total"),
        order_count=Sum("id") # Just to have something if total_orders is 0
    )
    
    return render(request, "ecommerce/customer_detail.html", {
        "project": project,
        "customer": customer,
        "orders": orders,
        "avg_order_value": stats["avg_order"] or 0,
    })


@login_required
def promo_codes_page(request):
    project = _selected_project(request)
    if project and request.GET.get("sync") == "1":
        connection = _wuilt_connection(project)
        if connection:
            try:
                sync_log = sync_wuilt_connection(connection)
                messages.success(request, f"تمت المزامنة بنجاح.")
            except Exception as exc:
                messages.error(request, f"فشلت المزامنة: {exc}")
        return redirect("ecommerce_promo_codes")

    promo_codes = PromoCode.objects.filter(project=project).order_by("-created_at") if project else PromoCode.objects.none()
    return render(request, "ecommerce/promo_codes.html", {"project": project, "promo_codes": promo_codes})


@login_required
def collections_page(request):
    project = _selected_project(request)
    if project and request.GET.get("sync") == "1":
        connection = _wuilt_connection(project)
        if connection:
            try:
                sync_log = sync_wuilt_connection(connection)
                messages.success(request, f"تمت المزامنة بنجاح.")
            except Exception as exc:
                messages.error(request, f"فشلت المزامنة: {exc}")
        return redirect("ecommerce_collections")
        
    collections = ProductCollection.objects.filter(project=project).order_by("-created_at") if project else ProductCollection.objects.none()
    return render(request, "ecommerce/collections.html", {"project": project, "collections": collections})


@login_required
def wuilt_api_settings(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    connection, _ = ApiConnection.objects.get_or_create(
        project=project,
        provider=WUILT_PROVIDER,
        defaults={
            "name": "Wuilt GraphQL API",
            "credentials": {"endpoint": DEFAULT_GRAPHQL_ENDPOINT, "locale": "en"},
            "created_by": request.user,
        },
    )
    if request.method == "POST":
        action = request.POST.get("action")
        credentials = connection.credentials or {}
        if action == "save":
            api_key = request.POST.get("api_key", "").strip()
            credentials["endpoint"] = request.POST.get("endpoint", DEFAULT_GRAPHQL_ENDPOINT).strip() or DEFAULT_GRAPHQL_ENDPOINT
            credentials["store_id"] = request.POST.get("store_id", "").strip()
            credentials["locale"] = request.POST.get("locale", "en").strip() or "en"
            if api_key:
                credentials["api_key"] = api_key
            connection.credentials = credentials
            connection.name = request.POST.get("name", connection.name).strip() or connection.name
            connection.status = "configured" if credentials.get("api_key") and credentials.get("store_id") else "missing_credentials"
            connection.save(update_fields=["credentials", "name", "status"])
            messages.success(request, "Wuilt settings saved.")
            return redirect("ecommerce_wuilt_api_settings")
        if action == "test":
            try:
                client = WuiltApiClient(credentials.get("endpoint"), credentials.get("api_key"))
                store = client.store_info(credentials.get("store_id"))
                messages.success(request, f"Connection successful: {store.get('name') or store.get('id') or 'Wuilt store'}.")
            except Exception as exc:
                messages.error(request, f"Connection test failed: {exc}")
            return redirect("ecommerce_wuilt_api_settings")
        if action == "sync":
            try:
                sync_log = sync_wuilt_connection(connection)
                messages.success(request, f"Sync completed: {sync_log.records_fetched} fetched, {sync_log.records_created} created, {sync_log.records_updated} updated.")
            except Exception as exc:
                messages.error(request, f"Sync failed: {exc}")
            return redirect("ecommerce_wuilt_api_settings")
    credentials = connection.credentials or {}
    webhook_url = request.build_absolute_uri("/ecommerce/webhooks/wuilt/")
    return render(request, "ecommerce/wuilt_api_settings.html", {
        "project": project,
        "connection": connection,
        "endpoint": credentials.get("endpoint") or DEFAULT_GRAPHQL_ENDPOINT,
        "store_id": credentials.get("store_id", ""),
        "locale": credentials.get("locale", "en"),
        "masked_api_key": masked_key(credentials.get("api_key", "")),
        "webhook_url": webhook_url,
        "sync_logs": connection.sync_logs.order_by("-started_at")[:10],
    })


@csrf_exempt
@require_POST
def wuilt_webhook(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    store_id = _store_id_from_webhook_payload(payload)
    project = _project_for_store_id(store_id)
    if not project:
        return JsonResponse({"error": "Unknown Wuilt store"}, status=404)
    event = payload.get("event", "")
    raw_event = RawApiEvent.objects.create(project=project, provider=WUILT_PROVIDER, endpoint=f"webhook:{event}", payload=payload)
    try:
        process_wuilt_webhook(project, event, payload.get("payload") or {})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=202)
    raw_event.processed = True
    raw_event.processed_at = timezone.now()
    raw_event.save(update_fields=["processed", "processed_at"])
    return HttpResponse("OK")


def _selected_project(request):
    projects = get_user_projects(request.user)
    project_id = request.GET.get("project") or request.session.get("current_project_id")
    if project_id:
        project = projects.filter(pk=project_id, project_type="ecommerce").first()
        if project:
            request.session["current_project_id"] = project.pk
            return project
    return projects.filter(project_type="ecommerce").first()


def _wuilt_connection(project):
    return ApiConnection.objects.filter(project=project, provider=WUILT_PROVIDER).order_by("-created_at").first()


def _project_for_store_id(store_id):
    if not store_id:
        return None
    connection = (
        ApiConnection.objects.filter(provider=WUILT_PROVIDER, credentials__store_id=store_id)
        .select_related("project")
        .order_by("-created_at")
        .first()
    )
    return connection.project if connection else None


def _store_id_from_webhook_payload(payload):
    metadata = payload.get("metadata") or {}
    body = payload.get("payload") or {}
    order = body.get("order") or {}
    product = body.get("product") or {}
    customer = body.get("customer") or {}
    return (
        metadata.get("storeId")
        or body.get("storeId")
        or order.get("storeId")
        or product.get("storeId")
        or customer.get("storeId")
    )
