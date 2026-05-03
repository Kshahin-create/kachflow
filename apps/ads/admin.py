from django.contrib import admin
from apps.ads.models import Ad, AdAccount, AdPerformanceMetric, AdSet, AdSpendDaily, Campaign


admin.site.register(AdAccount)
admin.site.register(Campaign)
admin.site.register(AdSet)
admin.site.register(Ad)
admin.site.register(AdSpendDaily)
admin.site.register(AdPerformanceMetric)
