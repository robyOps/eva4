from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, CartAddView, CheckoutView

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')

urlpatterns = router.urls + [
    path('cart/add/', CartAddView.as_view(), name='cart-add'),
    path('cart/checkout/', CheckoutView.as_view(), name='cart-checkout'),
]
