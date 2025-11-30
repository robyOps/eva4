from rest_framework import serializers
from django.utils import timezone
from .models import Product, Branch, Inventory, InventoryMovement, Supplier, Purchase, PurchaseItem
from apps.core.validators import validate_rut


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'company', 'sku', 'name', 'description', 'price', 'cost', 'category']
        read_only_fields = ['id', 'company']

    def validate(self, attrs):
        if attrs.get('price', 0) < 0 or attrs.get('cost', 0) < 0:
            raise serializers.ValidationError('Precio y costo deben ser >= 0')
        return attrs


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'company', 'name', 'address', 'phone']
        read_only_fields = ['id', 'company']


class InventorySerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = Inventory
        fields = ['id', 'company', 'branch', 'product', 'product_detail', 'stock', 'reorder_point']
        read_only_fields = ['id', 'company', 'stock']


class InventoryAdjustSerializer(serializers.Serializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=255, allow_blank=True)


class SupplierSerializer(serializers.ModelSerializer):
    rut = serializers.CharField(validators=[validate_rut])

    class Meta:
        model = Supplier
        fields = ['id', 'company', 'name', 'rut', 'contact_name', 'contact_email', 'contact_phone']
        read_only_fields = ['id', 'company']


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_cost']


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)

    class Meta:
        model = Purchase
        fields = ['id', 'company', 'branch', 'supplier', 'date', 'created_by', 'total_cost', 'items']
        read_only_fields = ['id', 'company', 'created_by', 'total_cost']

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError('La fecha no puede estar en el futuro')
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Debe incluir items')
        return value
