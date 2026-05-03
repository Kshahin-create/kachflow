class BaseConnector:
    provider = "base"

    def __init__(self, connection):
        self.connection = connection

    def authenticate(self):
        raise NotImplementedError

    def fetch_data(self):
        raise NotImplementedError

    def save_raw_response(self, payload):
        raise NotImplementedError

    def normalize_data(self, payload):
        raise NotImplementedError

    def update_system_tables(self, normalized):
        raise NotImplementedError

    def log_sync(self, status, **metadata):
        raise NotImplementedError


class SallaConnector(BaseConnector):
    provider = "salla"


class ShopifyConnector(BaseConnector):
    provider = "shopify"


class MetaAdsConnector(BaseConnector):
    provider = "meta_ads"


class TikTokAdsConnector(BaseConnector):
    provider = "tiktok_ads"


class GoogleSheetsConnector(BaseConnector):
    provider = "google_sheets"


class PaymentGatewayConnector(BaseConnector):
    provider = "payment_gateway"


class ShippingCompanyConnector(BaseConnector):
    provider = "shipping_company"
