from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import Company
from apps.core.validators import validate_rut


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('company', 'sku')

    def __str__(self):
        return self.name


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class Inventory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='inventories')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    stock = models.PositiveIntegerField(default=0)
    reorder_point = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('company', 'branch', 'product')


class InventoryMovement(models.Model):
    MOV_PURCHASE = 'PURCHASE'
    MOV_SALE = 'SALE'
    MOV_ADJUST = 'ADJUST'
    MOV_CHOICES = [
        (MOV_PURCHASE, 'Compra'),
        (MOV_SALE, 'Venta'),
        (MOV_ADJUST, 'Ajuste'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOV_CHOICES)
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)


class Supplier(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=255)
    rut = models.CharField(max_length=20, validators=[validate_rut])
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30)

    class Meta:
        unique_together = ('company', 'rut')

    def __str__(self):
        return self.name


class Purchase(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField()
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
