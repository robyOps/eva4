from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('shop/products/', views.product_list, name='shop-products'),
    path('shop/products/<int:pk>/', views.product_detail, name='shop-product-detail'),
    path('shop/cart/', views.cart_view, name='shop-cart'),
    path('shop/checkout/', views.checkout_view, name='shop-checkout'),
]
