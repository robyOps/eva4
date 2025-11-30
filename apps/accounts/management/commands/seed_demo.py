from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.models import Company, Subscription
from apps.inventory.models import Branch, Product, Inventory, Supplier


class Command(BaseCommand):
    help = 'Crea datos de demo'

    def handle(self, *args, **options):
        User = get_user_model()
        company, _ = Company.objects.get_or_create(name='Demo SA', rut='11111111-1')
        Subscription.objects.get_or_create(company=company, plan_name=Subscription.PLAN_ESTANDAR, start_date=timezone.now().date(), end_date=timezone.now().date(), active=True)
        admin, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'rut': '11111111-1', 'role': User.ROLE_ADMIN_CLIENTE, 'company': company})
        admin.set_password('admin123')
        admin.save()
        gerente, _ = User.objects.get_or_create(username='gerente', defaults={'email': 'gerente@example.com', 'rut': '22222222-2', 'role': User.ROLE_GERENTE, 'company': company})
        gerente.set_password('gerente123')
        gerente.save()
        vendedor, _ = User.objects.get_or_create(username='vendedor', defaults={'email': 'vendedor@example.com', 'rut': '33333333-3', 'role': User.ROLE_VENDEDOR, 'company': company})
        vendedor.set_password('vendedor123')
        vendedor.save()
        branch, _ = Branch.objects.get_or_create(company=company, name='Casa Matriz', address='Santiago', phone='123')
        prod, _ = Product.objects.get_or_create(company=company, sku='SKU1', defaults={'name': 'Producto Demo', 'description': 'Demo', 'price': 1000, 'cost': 500, 'category': 'General'})
        Inventory.objects.get_or_create(company=company, branch=branch, product=prod, defaults={'stock': 50, 'reorder_point': 5})
        Supplier.objects.get_or_create(company=company, name='Proveedor Demo', rut='44444444-4', contact_name='Juan', contact_email='proveedor@example.com', contact_phone='555-555')
        self.stdout.write(self.style.SUCCESS('Datos de demo creados'))
