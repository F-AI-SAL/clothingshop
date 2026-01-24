from django.contrib import admin
from django.urls import path, include
from two_factor.urls import urlpatterns as tf_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include((tf_urls[0], tf_urls[1]), namespace=tf_urls[1])),
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
    path("admin-dashboard/", include("store.admin_urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
