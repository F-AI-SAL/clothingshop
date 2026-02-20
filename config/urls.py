from django.contrib import admin
from django.urls import path, include
from two_factor import urls as tf_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include(tf_urls.urlpatterns)),
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
    path("admin-dashboard/", include("store.admin_urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
