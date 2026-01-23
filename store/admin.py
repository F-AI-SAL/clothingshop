from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    Category,
    Product,
    ProductImage,
    HomeBanner,
    FeaturedBanner,
    Order,
    OrderItem,
    ProductVariant,
    Coupon,
)


# ============================================================
# OPTIONAL: Admin Dashboard (works only if you wire custom site)
# ============================================================
class StoreAdminSite(admin.AdminSite):
    site_header = "La Rosa Admin"
    site_title = "La Rosa Admin"
    index_title = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="store-dashboard"),
        ]
        return extra + urls

    def dashboard_view(self, request):
        now = timezone.now()
        start = now - timedelta(days=7)

        revenue_7d = Order.objects.filter(created_at__gte=start).aggregate(s=Sum("total"))["s"] or 0
        orders_7d = Order.objects.filter(created_at__gte=start).count()

        by_status = list(
            Order.objects.values("status").annotate(c=Count("id")).order_by("-c")
        )

        top_products = list(
            OrderItem.objects.values("product__title")
            .annotate(q=Sum("qty"))
            .order_by("-q")[:8]
        )

        return TemplateResponse(request, "admin/store/dashboard.html", {
            "revenue_7d": revenue_7d,
            "orders_7d": orders_7d,
            "by_status": by_status,
            "top_products": top_products,
        })


# =========================
# PRODUCT IMAGES INLINE
# =========================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ("image", "alt_text", "sort_order")
    ordering = ("sort_order",)

# =========================
# ORDER INLINE
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "qty", "price", "line_total", "color", "size")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "phone", "email")
    ordering = ("-created_at",)
    inlines = [OrderItemInline]
    readonly_fields = ("subtotal", "discount", "shipping_cost", "total", "created_at")
    actions = [
        "mark_as_accepted",
        "mark_as_processing",
        "mark_as_packaging",
        "mark_as_shipped",
        "mark_as_delivered",
        "mark_as_cancelled",
        "mark_as_refunded",
    ]

    def _mark_status(self, request, queryset, status_key, label):
        updated = 0
        for order in queryset:
            if order.status == status_key:
                continue
            order.status = status_key
            order.save(update_fields=["status"])
            updated += 1
        self.message_user(request, f"{updated} order(s) marked as {label}.")

    def mark_as_accepted(self, request, queryset):
        self._mark_status(request, queryset, "accepted", "Accepted")
    mark_as_accepted.short_description = "Mark selected orders as Accepted"

    def mark_as_processing(self, request, queryset):
        self._mark_status(request, queryset, "processing", "Processing")
    mark_as_processing.short_description = "Mark selected orders as Processing"

    def mark_as_packaging(self, request, queryset):
        self._mark_status(request, queryset, "packaging", "Packaging")
    mark_as_packaging.short_description = "Mark selected orders as Packaging"

    def mark_as_shipped(self, request, queryset):
        self._mark_status(request, queryset, "shipped", "Shipped")
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    def mark_as_delivered(self, request, queryset):
        self._mark_status(request, queryset, "delivered", "Delivered")
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    def mark_as_cancelled(self, request, queryset):
        self._mark_status(request, queryset, "cancelled", "Cancelled")
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"

    def mark_as_refunded(self, request, queryset):
        self._mark_status(request, queryset, "refunded", "Refunded")
    mark_as_refunded.short_description = "Mark selected orders as Refunded"


# =========================
# HOME HERO BANNER
# =========================
@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("title",)
    ordering = ("-created_at",)


# =========================
# FEATURED COLLECTION BANNER
# =========================
@admin.register(FeaturedBanner)
class FeaturedBannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "is_active", "sort_order", "created_at")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle")
    ordering = ("sort_order", "-created_at")

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:42px;width:72px;object-fit:cover;'
                'border-radius:8px;border:1px solid #e5e7eb;" />',
                obj.image.url
            )
        return "—"
    preview.short_description = "Preview"


# =========================
# CATEGORY
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    ordering = ("parent__name", "sort_order", "name")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("name", "slug", "parent", "is_active", "sort_order")}),
        ("Category Card / Banner", {"fields": ("image", "tagline"), "classes": ("collapse",)}),
    )

# =========================
# PRODUCT VARIANTS INLINE (Inventory per size/color)
# =========================
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("color", "size", "stock_qty", "sku", "is_active")
    ordering = ("color", "size")

# =========================
# PRODUCT
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "is_active", "is_new", "created_at")
    list_filter = ("is_active", "is_new", "category")
    search_fields = ("title", "sku")
    ordering = ("-created_at",)
    prepopulated_fields = {"slug": ("title",)}

    # ✅ correct place for inlines
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "sku")}),
        ("Pricing & Description", {"fields": ("price", "description")}),
        ("Variants (simple list)", {"fields": ("colors", "sizes"), "classes": ("collapse",)}),
        ("Status", {"fields": ("is_active", "is_new")}),
    )

    class Media:
        js = ("store/admin/sortable.js",)

# =========================
# Coupon
# ========================= 
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "min_subtotal", "used_count", "max_uses")
    list_filter = ("is_active", "discount_type")
    search_fields = ("code",)
    ordering = ("-id",)      
