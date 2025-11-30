from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ProductViewSet, BranchViewSet, InventoryViewSet, InventoryAdjustView, SupplierViewSet, PurchaseViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchases', PurchaseViewSet, basename='purchase')

urlpatterns = router.urls + [
    path('inventory/adjust/', InventoryAdjustView.as_view(), name='inventory-adjust'),
]
