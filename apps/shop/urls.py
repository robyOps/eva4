from django.urls import path

from apps.inventory import web_views as inventory_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('shop/products/', views.product_list, name='shop-products'),
    path('shop/products/<int:pk>/', views.product_detail, name='shop-product-detail'),
    path('shop/cart/', views.cart_view, name='shop-cart'),
    path('shop/checkout/', views.checkout_view, name='shop-checkout'),
    path('tokens/', views.tokens_view, name='tokens'),
    path('suppliers/', inventory_views.suppliers_list, name='suppliers_list'),
    path('suppliers/create/', inventory_views.supplier_create, name='suppliers_create'),
    path('inventory/', inventory_views.inventory_by_branch, name='inventory_by_branch'),
    path('logout/', views.logout_view, name='logout'),
]
