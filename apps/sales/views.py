from rest_framework import viewsets, status, generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from apps.core.permissions import IsActive
from apps.accounts.permissions import IsAdminOrGerente, IsInternal
from apps.inventory.models import Inventory, InventoryMovement, Product, Branch
from .models import Sale, SaleItem, CartItem, Order, OrderItem
from .serializers import SaleSerializer, CartItemSerializer, OrderSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [IsActive(), IsAdminOrGerente()]
        return [IsActive(), IsInternal()]

    def get_queryset(self):
        qs = Sale.objects.filter(company=self.request.user.company)
        branch = self.request.query_params.get('branch')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if branch:
            qs = qs.filter(branch_id=branch)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        items_data = serializer.validated_data.pop('items')
        branch = serializer.validated_data['branch']
        if branch.company != user.company:
            raise ValidationError('Sucursal inválida')
        total = 0
        with transaction.atomic():
            sale = Sale.objects.create(company=user.company, seller=user, **serializer.validated_data)
            for item in items_data:
                product = item['product']
                quantity = item['quantity']
                unit_price = item['unit_price']
                inventory = Inventory.objects.select_for_update().get(company=user.company, branch=branch, product=product)
                if inventory.stock < quantity:
                    raise ValidationError('Stock insuficiente')
                inventory.stock -= quantity
                inventory.save()
                SaleItem.objects.create(sale=sale, **item)
                InventoryMovement.objects.create(
                    company=user.company,
                    branch=branch,
                    product=product,
                    movement_type=InventoryMovement.MOV_SALE,
                    quantity_delta=-quantity,
                    reason='Venta',
                    created_by=user,
                )
                total += quantity * unit_price
            sale.total = total
            sale.save()
        return sale


class CartAddView(generics.GenericAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsActive]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product, defaults={'quantity': quantity})
        if not created:
            cart_item.quantity = quantity
            cart_item.save()
        return Response({'detail': 'Agregado al carrito'})


class CheckoutView(generics.GenericAPIView):
    permission_classes = [IsActive]

    def post(self, request):
        branch_id = request.data.get('branch_id')
        branch = Branch.objects.filter(id=branch_id, company=request.user.company).first()
        if not branch:
            return Response({'detail': 'Sucursal inválida'}, status=status.HTTP_400_BAD_REQUEST)
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items:
            return Response({'detail': 'Carrito vacío'}, status=status.HTTP_400_BAD_REQUEST)
        total = 0
        with transaction.atomic():
            order = Order.objects.create(company=request.user.company, branch=branch, customer_name=request.user.username, customer_email=request.user.email, total=0)
            for ci in cart_items:
                inventory = Inventory.objects.select_for_update().get(company=request.user.company, branch=branch, product=ci.product)
                if inventory.stock < ci.quantity:
                    raise ValidationError('Stock insuficiente')
                inventory.stock -= ci.quantity
                inventory.save()
                price = ci.product.price
                total += price * ci.quantity
                OrderItem.objects.create(order=order, product=ci.product, quantity=ci.quantity, unit_price=price)
                InventoryMovement.objects.create(
                    company=request.user.company,
                    branch=branch,
                    product=ci.product,
                    movement_type=InventoryMovement.MOV_SALE,
                    quantity_delta=-ci.quantity,
                    reason='Checkout',
                    created_by=request.user,
                )
            order.total = total
            order.save()
            cart_items.delete()
        return Response(OrderSerializer(order).data)
