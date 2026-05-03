from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.dashboards.urls")),
    path("projects/", include("apps.projects.urls")),
    path("finance/", include("apps.finance.urls")),
    path("imports/", include("apps.imports.urls")),
    path("ecommerce/", include("apps.ecommerce.urls")),
    path("real-estate/", include("apps.real_estate.urls")),
    path("ads/", include("apps.ads.urls")),
    path("investments/", include("apps.investments.urls")),
    path("reports/", include("apps.reports.urls")),
    path("settings/", include("apps.audit.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/projects/", include("apps.projects.api_urls")),
    path("api/finance/", include("apps.finance.api_urls")),
    path("api/imports/", include("apps.imports.api_urls")),
    path("api/ecommerce/", include("apps.ecommerce.api_urls")),
    path("api/real-estate/", include("apps.real_estate.api_urls")),
    path("api/ads/", include("apps.ads.api_urls")),
    path("api/investments/", include("apps.investments.api_urls")),
    path("api/reports/", include("apps.reports.api_urls")),
    path("api/audit-log/", include("apps.audit.api_urls")),
    path("api/users/", include("apps.accounts.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
