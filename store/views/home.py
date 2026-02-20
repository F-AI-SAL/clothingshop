from django.shortcuts import render
from django.utils import timezone

from ..models import HomeBanner, FeaturedBanner, Product


# -----------------------
# HOME
# -----------------------
def home(request):
    banner = HomeBanner.objects.filter(is_active=True).first()

    # multiple featured (slider)
    now = timezone.now()
    featured_banners = FeaturedBanner.objects.filter(
        is_active=True
    ).order_by("sort_order", "-created_at")

    products = Product.objects.filter(is_active=True).order_by("-created_at")[:8]

    return render(request, "store/home.html", {
        "banner": banner,
        "featured_banners": featured_banners,   # if you use slider section
        "products": products,
    })
