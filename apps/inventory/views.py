from rest_framework import viewsets, status, generics
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from apps.core.permissions import IsActive
from apps.accounts.permissions import IsAdminOrGerente, IsInternal
from .models import Product, Branch, Inventory, InventoryMovement, Supplier, Purchase, PurchaseItem
from .serializers import (
    ProductSerializer, BranchSerializer, InventorySerializer, InventoryAdjustSerializer,
    SupplierSerializer, PurchaseSerializer
)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsActive(), IsAdminOrGerente()]

    def get_queryset(self):
        qs = Product.objects.all()
        if self.action in ['list', 'retrieve']:
            return qs
        return qs.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        serializer.save(company=self.request.user.company)


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsActive, IsInternal]

    def get_queryset(self):
        return Branch.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        user = self.request.user
        subscription = getattr(user.company, 'subscription', None)
        if subscription and subscription.branch_limit:
            if Branch.objects.filter(company=user.company).count() >= subscription.branch_limit:
                raise ValidationError('Límite de sucursales alcanzado para el plan actual')
        serializer.save(company=user.company)

    @action(detail=True, methods=['get'], url_path='inventory')
    def inventory(self, request, pk=None):
        branch = self.get_object()
        inventories = Inventory.objects.filter(company=request.user.company, branch=branch)
        serializer = InventorySerializer(inventories, many=True)
        return Response(serializer.data)


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsActive, IsInternal]

    def get_queryset(self):
        qs = Inventory.objects.filter(company=self.request.user.company)
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

class InventoryAdjustView(generics.GenericAPIView):
    serializer_class = InventoryAdjustSerializer
    permission_classes = [IsActive, IsAdminOrGerente]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        branch = data['branch']
        product = data['product']
        qty = data['quantity_delta']
        if branch.company != request.user.company or product.company != request.user.company:
            return Response({'detail': 'Operación inválida'}, status=status.HTTP_400_BAD_REQUEST)
        inventory, _ = Inventory.objects.get_or_create(company=request.user.company, branch=branch, product=product, defaults={'stock': 0})
        new_stock = inventory.stock + qty
        if new_stock < 0:
            return Response({'detail': 'Stock no puede ser negativo'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            inventory.stock = new_stock
            inventory.save()
            InventoryMovement.objects.create(
                company=request.user.company,
                branch=branch,
                product=product,
                movement_type=InventoryMovement.MOV_ADJUST,
                quantity_delta=qty,
                reason=data.get('reason', ''),
                created_by=request.user,
            )
        return Response({'detail': 'Ajuste aplicado', 'stock': inventory.stock})


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsActive, IsAdminOrGerente]

    def get_queryset(self):
        return Supplier.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsActive, IsAdminOrGerente]

    def get_queryset(self):
        return Purchase.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        user = self.request.user
        items_data = serializer.validated_data.pop('items')
        branch = serializer.validated_data['branch']
        supplier = serializer.validated_data['supplier']
        if branch.company != user.company or supplier.company != user.company:
            raise ValidationError('Sucursal o proveedor inválido')
        purchase = Purchase.objects.create(company=user.company, created_by=user, **serializer.validated_data)
        total = 0
        with transaction.atomic():
            for item in items_data:
                product = item['product']
                quantity = item['quantity']
                unit_cost = item['unit_cost']
                total += quantity * unit_cost
                PurchaseItem.objects.create(purchase=purchase, **item)
                inventory, _ = Inventory.objects.get_or_create(company=user.company, branch=purchase.branch, product=product, defaults={'stock': 0})
                inventory.stock += quantity
                inventory.save()
                InventoryMovement.objects.create(
                    company=user.company,
                    branch=purchase.branch,
                    product=product,
                    movement_type=InventoryMovement.MOV_PURCHASE,
                    quantity_delta=quantity,
                    reason='Compra',
                    created_by=user,
                )
        purchase.total_cost = total
        purchase.save()
        return purchase
