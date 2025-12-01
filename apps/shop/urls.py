from django.urls import path

from apps.inventory import web_views as inventory_views
from apps.sales import web_views as sales_web_views
from apps.reports import web_views as reports_web_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('shop/products/', views.product_list, name='shop-products'),
    path('shop/products/<int:pk>/', views.product_detail, name='shop-product-detail'),
    path('shop/cart/add/', views.cart_add_view, name='cart_add'),
    path('shop/cart/', views.cart_view, name='shop-cart'),
    path('shop/checkout/', views.checkout_view, name='shop-checkout'),
    path('shop/orders/', views.orders_list_view, name='shop_orders'),
    path('shop/orders/<int:pk>/', views.order_detail_view, name='shop_order_detail'),
    path('purchases/new/', inventory_views.purchase_create, name='purchase_create'),
    path('sales/', sales_web_views.sales_list, name='sales_list'),
    path('reports/stock/', reports_web_views.stock_report, name='report_stock'),
    path('reports/suppliers/', reports_web_views.suppliers_report, name='report_suppliers'),
    path('branches/', inventory_views.branches_list, name='branches_list'),
    path('branches/new/', inventory_views.branch_create, name='branches_create'),
    path('subscription/', views.subscription_detail, name='subscription_detail'),
    path('users/new/', views.user_create_view, name='user_create'),
    path('pos/new-sale/', sales_web_views.pos_new_sale, name='pos_new_sale'),
    path('tokens/', views.tokens_view, name='tokens'),
    path('suppliers/', inventory_views.suppliers_list, name='suppliers_list'),
    path('suppliers/create/', inventory_views.supplier_create, name='suppliers_create'),
    path('inventory/', inventory_views.inventory_by_branch, name='inventory_by_branch'),
    path('logout/', views.logout_view, name='logout'),
]
