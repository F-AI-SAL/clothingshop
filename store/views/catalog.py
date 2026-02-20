from django.shortcuts import render, get_object_or_404

from ..models import Product


# -----------------------
# PRODUCT LIST
# -----------------------
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("-created_at")

    cat_slug = request.GET.get("cat")
    if cat_slug:
        products = products.filter(category__slug=cat_slug)

    return render(request, "store/product_list.html", {
        "products": products,
    })


# -----------------------
# PRODUCT DETAIL
# -----------------------
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    images = product.images.all()

    related = Product.objects.filter(
        is_active=True,
        category=product.category
    ).exclude(id=product.id).order_by("-created_at")[:4]

    return render(request, "store/product_detail.html", {
        "product": product,
        "images": images,
        "related": related,
    })
