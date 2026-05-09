from datetime import date
from decimal import Decimal, InvalidOperation
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone

from apps.ecommerce.models import Customer, Order, OrderItem, Product, ProductCollection, PromoCode
from apps.integrations.models import RawApiEvent, SyncLog


WUILT_PROVIDER = "wuilt"
DEFAULT_GRAPHQL_ENDPOINT = "https://graphql.wuilt.com/"


class WuiltApiError(Exception):
    pass


class WuiltApiClient:
    def __init__(self, endpoint=DEFAULT_GRAPHQL_ENDPOINT, api_key="", timeout=90):
        self.endpoint = endpoint or DEFAULT_GRAPHQL_ENDPOINT
        self.api_key = api_key
        self.timeout = timeout

    def graphql(self, query, variables=None, extra_headers=None):
        if not self.api_key:
            raise WuiltApiError("Wuilt API key is not configured.")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        if extra_headers:
            headers.update(extra_headers)
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        request = Request(self.endpoint, headers=headers, method="POST", data=payload)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise WuiltApiError(f"Wuilt API error {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError) as exc:
            raise WuiltApiError(f"Could not connect to Wuilt API: {exc}") from exc
        if data.get("errors"):
            message = "; ".join(str(error.get("message", error)) for error in data["errors"])
            raise WuiltApiError(message)
        return data.get("data", {})

    def store_info(self, store_id):
        return self.graphql(
            """
            query GetStoreInfo($storeId: ID!) {
              store(id: $storeId) {
                id
                name
              }
            }
            """,
            {"storeId": store_id},
        )

    def products(self, store_id, locale="en", first=50, offset=0):
        return self.graphql(
            """
            query ListStoreProducts($connection: ProductsConnectionInput, $filter: ProductsFilterInput, $locale: String) {
              products(connection: $connection, filter: $filter, locale: $locale) {
                totalCount
                nodes {
                  id
                  title
                  handle
                  type
                  status
                  isVisible
                  isArchived
                  shortDescription
                  descriptionHtml
                  createdAt
                  updatedAt
                  images {
                    id
                    src
                    altText
                  }
                  categories {
                    id
                    name
                  }
                  variants(first: 50) {
                    nodes {
                      id
                      title
                      sku
                      quantity
                      price {
                        amount
                        currencyCode
                      }
                      compareAtPrice {
                        amount
                        currencyCode
                      }
                      cost {
                        amount
                        currencyCode
                      }
                      image {
                        id
                        src
                      }
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """,
            {
                "connection": {"first": first, "offset": offset, "sortBy": "createdAt", "sortOrder": "desc"},
                "filter": {"status": "ACTIVE", "storeIds": [store_id]},
                "locale": locale,
            },
        )

    def orders(self, store_id, first=50, offset=0):
        return self.graphql(
            """
            query ListStoreOrders($connection: OrdersConnectionInput, $filter: OrdersFilterInput, $storeId: ID!) {
              orders(connection: $connection, filter: $filter, storeId: $storeId) {
                totalCount
                nodes {
                  id
                  orderSerial
                  createdAt
                  status
                  fulfillmentStatus
                  paymentStatus
                  shippingStatus
                  isCanceled
                  isArchived
                  isViewed
                  totalPrice { amount currencyCode }
                  subtotal { amount currencyCode }
                  receipt {
                    total { amount currencyCode }
                    subtotal { amount currencyCode }
                    shipping { amount currencyCode }
                    discount { amount currencyCode }
                    tax { amount currencyCode }
                  }
                  shippingRateCost { amount currencyCode }
                  shippingAddress {
                    addressLine1
                    addressLine2
                    phone
                    postalCode
                    areaSnapshot {
                      cityName
                      stateName
                      countryName
                    }
                  }
                  shipmentDetails {
                    trackingURL
                    shippedWith
                    airWayBill
                    orderTrackingNumber
                  }
                  paymentIntent {
                    id
                    provider
                    paymentProvider
                  }
                  customer { name email phone }
                  packagingDetails {
                    weight
                    extraWeight
                    volumetricWeight
                  }
                  tags { id name color }
                  items {
                    id
                    title
                    quantity
                    ... on SimpleItem {
                      productSnapshot { id title handle }
                      variantSnapshot { id sku price { amount currencyCode } }
                    }
                  }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
            """,
            {
                "connection": {"first": first, "offset": offset, "sortBy": "createdAt", "sortOrder": "desc"},
                "filter": {"isArchived": False},
                "storeId": store_id,
            },
        )

    def collections(self, store_id, locale="en", first=50, offset=0):
        return self.graphql(
            """
            query ListStoreCollections($connection: ProductCollectionConnectionInput, $filter: ProductCollectionFilterInput, $locale: String) {
              collections(connection: $connection, filter: $filter, locale: $locale) {
                totalCount
                nodes {
                  id
                  title
                  handle
                  description
                  descriptionHtml
                  productsCount
                  image {
                    id
                    src
                    altText
                  }
                  isVisible
                  isArchived
                  createdAt
                  updatedAt
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """,
            {
                "connection": {"first": first, "offset": offset, "sortBy": "createdAt", "sortOrder": "desc"},
                "filter": {"storeId": store_id},
                "locale": locale,
            },
        )

    def abandoned_checkouts(self, store_id, first=50, offset=0):
        return self.graphql(
            """
            query ListAbandonedCheckouts($storeId: ID!, $connection: OrdersConnectionInput) {
              adminQueries(storeId: $storeId) {
                checkout {
                  abandonedCheckouts(connection: $connection) {
                    totalCount
                    nodes {
                      id
                      orderSerial
                      createdAt
                      status
                      totalPrice { amount currencyCode }
                      customer { name email phone }
                    }
                  }
                }
              }
            }
            """,
            {"storeId": store_id, "connection": {"first": first, "offset": offset}},
        )

    def promo_codes(self, store_id, first=50, offset=0):
        # Even more basic promo code query
        return self.graphql(
            """
            query ListPromoCodes($storeId: ID!, $connection: PromoCodesConnectionInput) {
              adminQueries(storeId: $storeId) {
                promoCode {
                  promoCodes(connection: $connection) {
                    totalCount
                    nodes {
                      id
                      code
                      type
                      status
                      percentageOff
                      fixedAmount
                      usageLimit
                      numberOfUsage
                      isArchived
                    }
                  }
                }
              }
            }
            """,
            {"storeId": store_id, "connection": {"first": first, "offset": offset}},
        )

    def discounts(self, store_id, first=50, offset=0):
        # Even more basic discount query
        return self.graphql(
            """
            query ListDiscounts($storeId: ID!) {
              adminQueries(storeId: $storeId) {
                discounts {
                  discounts {
                    id
                    title
                    status
                    percentage
                    amount { amount currencyCode }
                  }
                }
              }
            }
            """,
            {"storeId": store_id},
        )

    def customers(self, store_id=None, first=50, offset=0):
        # Trying root query for customers with CustomersConnectionInput
        return self.graphql(
            """
            query ListCustomers($connection: CustomersConnectionInput) {
              customers(connection: $connection) {
                totalCount
                nodes {
                  id
                  firstName
                  lastName
                  email
                  phone
                  isActive
                  isVerified
                  createdAt
                  addresses {
                    addressLine1
                    addressLine2
                    phone
                    postalCode
                    areaSnapshot { cityName stateName countryName }
                  }
                  tags { id name color }
                }
              }
            }
            """,
            {"connection": {"first": first, "offset": offset}},
        )


def masked_key(api_key):
    if not api_key:
        return ""
    if len(api_key) <= 10:
        return "********"
    return f"{api_key[:8]}...{api_key[-4:]}"


def sync_wuilt_connection(api_connection):
    credentials = api_connection.credentials or {}
    store_id = credentials.get("store_id") or ""
    if not store_id:
        raise WuiltApiError("Store ID is required before syncing.")
    client = WuiltApiClient(
        endpoint=credentials.get("endpoint") or DEFAULT_GRAPHQL_ENDPOINT,
        api_key=credentials.get("api_key") or "",
        timeout=int(credentials.get("timeout") or 90),
    )
    sync_log = SyncLog.objects.create(api_connection=api_connection, status="running")
    fetched = created = updated = 0
    try:
        store_payload = client.store_info(store_id)
        locale = credentials.get("locale") or "en"
        products_payload = client.products(store_id, locale=locale)
        orders_payload = client.orders(store_id)
        
        collections_payload = {}
        try:
            collections_payload = client.collections(store_id, locale=locale)
        except Exception as e:
            print(f"Error fetching collections: {e}")
            
        customers_payload = {}
        try:
            customers_payload = client.customers(store_id)
        except Exception:
            pass
            
        promo_codes_payload = {}
        try:
            promo_codes_payload = client.promo_codes(store_id)
        except Exception as e:
            print(f"Error fetching promo codes: {e}")
            
        discounts_payload = {}
        try:
            discounts_payload = client.discounts(store_id)
        except Exception as e:
            print(f"Error fetching discounts: {e}")
            
        abandoned_payload = {}
        try:
            abandoned_payload = client.abandoned_checkouts(store_id)
        except Exception:
            pass

        RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="store", payload=store_payload)
        RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="products", payload=products_payload)
        RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="orders", payload=orders_payload)
        
        if collections_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="collections", payload=collections_payload)
        if customers_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="customers", payload=customers_payload)
        if promo_codes_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="promo_codes", payload=promo_codes_payload)
        if discounts_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="discounts", payload=discounts_payload)
        if abandoned_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=WUILT_PROVIDER, endpoint="abandoned_checkouts", payload=abandoned_payload)

        product_rows = _connection_nodes(products_payload)
        order_rows = _connection_nodes(orders_payload)
        collection_rows = _connection_nodes(collections_payload)
        customer_rows = _connection_nodes(customers_payload)
        promo_code_rows = _connection_nodes(promo_codes_payload)
        discount_rows = _connection_nodes(discounts_payload)
        abandoned_rows = _connection_nodes(abandoned_payload)

        fetched = len(product_rows) + len(order_rows) + len(collection_rows) + len(customer_rows) + len(promo_code_rows) + len(discount_rows) + len(abandoned_rows)
        with transaction.atomic():
            if collection_rows:
                sync_collections(api_connection.project, collection_rows)
            if promo_code_rows:
                sync_promo_codes(api_connection.project, promo_code_rows)
            if discount_rows:
                sync_promo_codes(api_connection.project, discount_rows)
            if customer_rows:
                sync_customers(api_connection.project, customer_rows)
            if abandoned_rows:
                sync_abandoned_checkouts(api_connection.project, abandoned_rows)
            
            product_created, product_updated = sync_products(api_connection.project, product_rows)
            order_created, order_updated = sync_orders(api_connection.project, order_rows)
            created += product_created + order_created
            updated += product_updated + order_updated
            api_connection.status = "active"
            api_connection.last_sync_at = timezone.now()
            api_connection.save(update_fields=["status", "last_sync_at"])

        sync_log.status = "completed"
        sync_log.finished_at = timezone.now()
        sync_log.records_fetched = fetched
        sync_log.records_created = created
        sync_log.records_updated = updated
        sync_log.save(update_fields=["status", "finished_at", "records_fetched", "records_created", "records_updated"])
        return sync_log
    except Exception as exc:
        api_connection.status = "failed"
        api_connection.save(update_fields=["status"])
        sync_log.status = "failed"
        sync_log.finished_at = timezone.now()
        sync_log.records_fetched = fetched
        sync_log.records_created = created
        sync_log.records_updated = updated
        sync_log.error_message = str(exc)
        sync_log.save(update_fields=["status", "finished_at", "records_fetched", "records_created", "records_updated", "error_message"])
        raise


def sync_products(project, rows):
    created = updated = 0
    for row in rows:
        product, was_created = upsert_product(project, row)
        if not product:
            continue
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def upsert_product(project, row):
    external_id = _text(row.get("id"))
    handle = _text(row.get("handle"))
    if not external_id:
        return None, False

    product = Product.objects.filter(project=project, external_id=external_id).first()
    was_created = product is None
    if was_created:
        product = Product(project=project, external_id=external_id)

    product.handle = handle
    product.name = _text(row.get("title"))
    product.description = _text(row.get("descriptionHtml") or row.get("shortDescription"))
    product.status = _text(row.get("status") or "ACTIVE")
    product.product_type = _text(row.get("type"))
    product.tags = row.get("tags") or []
    product.images_json = row.get("images") or []

    categories = row.get("categories") or []
    if categories and categories[0]:
        product.category = _text(categories[0].get("name") or categories[0].get("title"))

    # Variants and Pricing
    variants_payload = row.get("variants") or {}
    variant_nodes = _connection_nodes(variants_payload)
    product.variants_json = [v for v in variant_nodes if v]

    if product.variants_json:
        v0 = product.variants_json[0]
        product.sku = _text(v0.get("sku"))
        product.selling_price = _decimal((v0.get("price") or {}).get("amount"))
        product.compare_at_price = _decimal((v0.get("compareAtPrice") or {}).get("amount"))
        product.cost_price = _decimal((v0.get("cost") or {}).get("amount"))
        product.currency = _text((v0.get("price") or {}).get("currencyCode") or "SAR")
        product.stock_quantity = int(v0.get("quantity") or 0)
    else:
        product.sku = _text(row.get("sku"))
        product.selling_price = 0
        product.stock_quantity = 0

    product.raw_data = row
    product.save()

    # Link collections
    collection_ids = _connection_nodes(row.get("collectionIds") or row.get("collections") or [])
    if collection_ids:
        # If collection_ids is a list of objects with id, extract ids
        ids = [c.get("id") if isinstance(c, dict) else c for c in collection_ids]
        col_objs = ProductCollection.objects.filter(project=project, external_id__in=ids)
        product.collections.set(col_objs)

    return product, was_created


def sync_collections(project, rows):
    for row in rows:
        external_id = _text(row.get("id"))
        if not external_id:
            continue
        col = ProductCollection.objects.filter(project=project, external_id=external_id).first()
        if not col:
            col = ProductCollection(project=project, external_id=external_id)
        col.title = _text(row.get("title"))
        col.handle = _text(row.get("handle"))
        col.description = _text(row.get("descriptionHtml") or row.get("description"))
        col.products_count = _int(row.get("productsCount"))
        img = row.get("image") or {}
        col.image_url = _text(img.get("src") or img.get("url"))
        col.raw_data = row
        col.save()


def sync_promo_codes(project, rows):
    for row in rows:
        external_id = _text(row.get("id"))
        if not external_id:
            continue
        promo = PromoCode.objects.filter(project=project, external_id=external_id).first()
        if not promo:
            promo = PromoCode(project=project, external_id=external_id)
        promo.code = _text(row.get("code") or row.get("title"))
        promo.description = _text(row.get("description") or row.get("title"))
        promo.promo_type = _text(row.get("type"))
        promo.status = _text(row.get("status") or "ACTIVE")
        promo.percentage_off = float(row.get("percentageOff") or row.get("percentage") or 0)
        
        fixed_amount = row.get("fixedAmount")
        if not fixed_amount and row.get("amount"):
            fixed_amount = row.get("amount").get("amount")
        promo.fixed_amount = _decimal(fixed_amount)
        
        promo.usage_limit = int(row.get("usageLimit") or 0)
        promo.number_of_usage = int(row.get("numberOfUsage") or 0)
        promo.is_archived = bool(row.get("isArchived"))
        promo.raw_data = row
        promo.save()


def sync_customers(project, rows):
    for row in rows:
        upsert_customer(project, row)


def sync_abandoned_checkouts(project, rows):
    for row in rows:
        row["is_abandoned"] = True
        upsert_order(project, row)


def sync_orders(project, rows):
    created = updated = 0
    for row in rows:
        order, was_created = upsert_order(project, row)
        if not order:
            continue
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def upsert_order(project, row):
    external_id = _text(row.get("id") or row.get("_id") or row.get("orderId"))
    serial = _text(row.get("orderSerial") or row.get("refCode") or external_id)
    if not serial:
        return None, False
    customer = upsert_customer(project, row.get("customer") or row.get("contactInfo") or {})
    receipt = row.get("receipt") or {}
    total = row.get("totalPrice") or receipt.get("total") or {}
    subtotal = row.get("subtotal") or receipt.get("subtotal") or total
    shipping = row.get("shippingRateCost") or receipt.get("shipping") or {}
    discount = receipt.get("discount") or {}
    tax = receipt.get("tax") or {}

    order = None
    if external_id:
        order = Order.objects.filter(project=project, external_id=external_id).first()
    if not order:
        order = Order.objects.filter(project=project, order_number=serial).first()
    was_created = order is None
    if was_created:
        order = Order(project=project, order_number=serial, order_date=_date(row.get("createdAt")) or date.today())

    order.external_id = external_id
    order.order_number = serial
    order.customer = customer
    order.status = _text(row.get("status"))
    order.fulfillment_status = _text(row.get("fulfillmentStatus"))
    order.payment_status = _text(row.get("paymentStatus"))
    order.shipping_status = _text(row.get("shippingStatus"))
    order.is_viewed = bool(row.get("isViewed"))
    order.is_canceled = bool(row.get("isCanceled"))
    order.is_archived = bool(row.get("isArchived"))
    order.is_abandoned = bool(row.get("is_abandoned", False))

    shipment = row.get("shipmentDetails") or {}
    order.tracking_number = _text(shipment.get("orderTrackingNumber") or shipment.get("airWayBill"))
    order.tracking_url = _text(shipment.get("trackingURL"))

    payment = row.get("paymentIntent") or {}
    order.payment_intent_id = _text(payment.get("id"))
    order.payment_method = _text(payment.get("paymentProvider") or payment.get("provider"))

    order.shipping_address_json = row.get("shippingAddress") or {}
    order.packaging_details_json = row.get("packagingDetails") or {}
    order.tags_json = _connection_nodes(row.get("tags") or [])

    order.gross_total = _decimal(subtotal.get("amount"))
    order.discount = _decimal(discount.get("amount"))
    order.shipping_fee = _decimal(shipping.get("amount"))
    order.net_total = _decimal(total.get("amount"))
    order.currency = _text(total.get("currencyCode") or total.get("currency") or project.base_currency or "EGP")[:8]
    order.source = WUILT_PROVIDER
    order.raw_data = row
    order.save()
    _sync_order_items(order, row.get("items") or [])
    return order, was_created


def upsert_customer(project, row):
    if not row:
        return None
    external_id = _text(row.get("id") or row.get("_id") or row.get("customerId"))
    name = _text(row.get("name") or " ".join(filter(None, [_text(row.get("firstName")), _text(row.get("lastName"))])))
    email = _text(row.get("email"))
    phone = _text(row.get("phone"))
    if not external_id and not (name or email or phone):
        return None
    customer = None
    if external_id:
        customer = Customer.objects.filter(project=project, external_id=external_id).first()
    if not customer and email:
        customer = Customer.objects.filter(project=project, email=email).first()
    if not customer and phone:
        customer = Customer.objects.filter(project=project, phone=phone).first()
    if not customer:
        customer = Customer(project=project, name=name or email or phone or external_id)
    customer.external_id = external_id
    customer.name = name or customer.name
    customer.first_name = _text(row.get("firstName"))
    customer.last_name = _text(row.get("lastName"))
    customer.email = email
    customer.phone = phone
    customer.is_active = bool(row.get("isActive", True))
    customer.is_verified = bool(row.get("isVerified", False))
    customer.addresses_json = _connection_nodes(row.get("addresses") or [])
    customer.tags_json = _connection_nodes(row.get("tags") or [])
    customer.country = _text(row.get("countryName") or row.get("country"))
    customer.city = _text(row.get("cityName") or row.get("city"))
    customer.raw_data = row
    customer.save()
    return customer


def process_wuilt_webhook(project, event, payload):
    event = (event or "").upper()
    if event in {"PRODUCT_CREATED", "PRODUCT_UPDATED"}:
        product = payload.get("product") or payload
        upsert_product(project, product)
    elif event in {"CUSTOMER_CREATED", "CUSTOMER_UPDATED"}:
        customer = payload.get("customer") or payload
        upsert_customer(project, customer)
    elif event in {"ORDER_PLACED", "ORDER_UPDATED", "ORDER_CANCELED"}:
        order = payload.get("order") or payload
        upsert_order(project, order)


def _sync_order_items(order, rows):
    existing = {item.product_name: item for item in order.items.all()}
    for row in rows:
        product_snapshot = row.get("productSnapshot") or row.get("product") or {}
        variant_snapshot = row.get("variantSnapshot") or row.get("variant") or {}
        title = _text(row.get("title") or product_snapshot.get("title") or "Wuilt item")
        quantity = _decimal(row.get("quantity") or 1)
        subtotal = row.get("subtotal") or row.get("totalPrice") or {}
        price = variant_snapshot.get("price") or row.get("price") or subtotal
        item = existing.get(title) or OrderItem(order=order, product_name=title)
        item.quantity = quantity
        item.unit_price = _decimal(price.get("amount"))
        item.total_price = _decimal(subtotal.get("amount")) or (item.unit_price * quantity)
        item.save()


def _connection_nodes(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("nodes"), list):
            return value["nodes"]
        if isinstance(value.get("edges"), list):
            return [edge.get("node") for edge in value["edges"] if edge.get("node")]
        
        # Search in common top-level keys
        for key in ("adminQueries", "products", "orders", "customers", "collections", "discounts", "promoCode", "promoCodes", "abandonedCheckouts", "getAllPromoCodes", "getAllDiscounts"):
            if key in value:
                return _connection_nodes(value[key])
        
        # If not found in keys, try a deeper search in dictionary values
        for v in value.values():
            if isinstance(v, (dict, list)):
                res = _connection_nodes(v)
                if res: return res
    return []


def _first_variant(row):
    variants = row.get("variants") or row.get("productVariants") or []
    if isinstance(variants, dict):
        variants = variants.get("nodes") or variants.get("edges") or []
    if variants and isinstance(variants[0], dict) and variants[0].get("node"):
        return variants[0]["node"]
    return variants[0] if variants else {}


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _decimal(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _date(value):
    value = _text(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
