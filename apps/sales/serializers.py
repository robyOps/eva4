from rest_framework import serializers
from django.utils import timezone
from apps.inventory.models import Branch, Product, Inventory, InventoryMovement
from .models import Sale, SaleItem, CartItem, Order, OrderItem


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ['id', 'company', 'branch', 'seller', 'total', 'payment_method', 'created_at', 'items']
        read_only_fields = ['id', 'company', 'seller', 'total', 'created_at']

    def validate_branch(self, value):
        user = self.context['request'].user
        if value.company != user.company:
            raise serializers.ValidationError('Sucursal inválida')
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Debe incluir items')
        for item in value:
            if item['quantity'] < 1 or item['unit_price'] < 0:
                raise serializers.ValidationError('Cantidad y precio inválidos')
        return value


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['product', 'quantity']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'company', 'branch', 'customer_name', 'customer_email', 'status', 'total', 'created_at', 'items']
        read_only_fields = ['id', 'company', 'total', 'created_at', 'status']
