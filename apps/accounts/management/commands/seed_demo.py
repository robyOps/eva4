import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Company, Plan, PlanFeature, Subscription
from apps.inventory.models import (
    Branch,
    Inventory,
    InventoryMovement,
    Product,
    Purchase,
    PurchaseItem,
    Supplier,
)
from apps.sales.models import CartItem, Order, OrderItem, Sale, SaleItem


class Command(BaseCommand):
    help = 'Crea datos de demo'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Reinicia los datos de demo')
        parser.add_argument('--products', type=int, default=200)
        parser.add_argument('--suppliers', type=int, default=30)
        parser.add_argument('--branches', type=int, default=5)
        parser.add_argument('--purchases', type=int, default=80)
        parser.add_argument('--sales', type=int, default=180)
        parser.add_argument('--orders', type=int, default=120)
        parser.add_argument('--items-per-purchase', type=int, default=6)
        parser.add_argument('--items-per-sale', type=int, default=4)
        parser.add_argument('--items-per-order', type=int, default=3)

    def handle(self, *args, **options):
        User = get_user_model()
        reset = options.get('reset')
        additional_specs = [
            {
                'company': ('Logística Pacífico Ltda.', self._rut_with_dv(76543210), 'BASICO'),
                'users': [
                    ('catalina.vera', User.ROLE_ADMIN_CLIENTE, 'catalina.vera@pacifico.cl', self._rut_with_dv(13875432)),
                    ('rodrigo.palma', User.ROLE_GERENTE, 'rodrigo.palma@pacifico.cl', self._rut_with_dv(14789654)),
                    ('francisca.munoz', User.ROLE_VENDEDOR, 'francisca.munoz@pacifico.cl', self._rut_with_dv(18234567)),
                ],
            },
            {
                'company': ('Tecnored Chile S.A.', self._rut_with_dv(77345678), 'ESTANDAR'),
                'users': [
                    ('alejandra.perez', User.ROLE_ADMIN_CLIENTE, 'alejandra.perez@tecnored.cl', self._rut_with_dv(15987456)),
                    ('jorge.acevedo', User.ROLE_GERENTE, 'jorge.acevedo@tecnored.cl', self._rut_with_dv(16874521)),
                    ('isidora.galvez', User.ROLE_VENDEDOR, 'isidora.galvez@tecnored.cl', self._rut_with_dv(17654329)),
                ],
            },
            {
                'company': ('Energix Solar Group', self._rut_with_dv(70459812), 'PREMIUM'),
                'users': [
                    ('marcela.espinoza', User.ROLE_ADMIN_CLIENTE, 'marcela.espinoza@energix.cl', self._rut_with_dv(19876543)),
                    ('daniel.rivera', User.ROLE_GERENTE, 'daniel.rivera@energix.cl', self._rut_with_dv(20567891)),
                    ('constanza.rojas', User.ROLE_VENDEDOR, 'constanza.rojas@energix.cl', self._rut_with_dv(21456780)),
                ],
            },
        ]
        usernames = ['superadmin', 'ana.rios', 'matias.urrutia', 'carlos.fuentes'] + [
            username for spec in additional_specs for username, *_ in spec['users']
        ]
        company_name = 'Comercial Andes SpA'
        company_rut = self._rut_with_dv(76123456)
        all_company_ruts = [company_rut] + [spec['company'][1] for spec in additional_specs]

        if reset:
            self._reset_demo_data(all_company_ruts, usernames)

        with transaction.atomic():
            self._ensure_seed_plans()
            super_admin = self._ensure_super_admin(User)
            company = self._ensure_company(company_name, company_rut)
            self._ensure_subscription(company)
            users = self._ensure_users(User, company)
            extra_companies = self._ensure_additional_companies(User, additional_specs)

            existing_products = Product.objects.filter(company=company).count()
            if not reset and existing_products > max(50, options['products'] // 2):
                self.stdout.write(self.style.WARNING('Ya existen datos de demo, usa --reset para recrearlos.'))
                return

            branches = self._ensure_branches(company, options['branches'])
            products = self._ensure_products(company, options['products'])
            suppliers = self._ensure_suppliers(company, options['suppliers'])

            inventory_cache = self._seed_inventories(company, branches, products)
            self._create_purchases(company, branches, suppliers, products, inventory_cache, users['gerente'], options)
            self._create_sales(company, branches, products, inventory_cache, users['vendedor'], options)
            self._create_orders(company, branches, products, inventory_cache, options)
            self._create_cart_items(users['vendedor'], products)

            Inventory.objects.bulk_update(list(inventory_cache.values()), ['stock', 'reorder_point'])

            for extra in extra_companies:
                self._seed_additional_company_data(extra, options)

        self._print_summary(company, usernames, super_admin, extra_companies)

    def _rut_with_dv(self, number: int) -> str:
        digits = str(number)
        factors = [2, 3, 4, 5, 6, 7]
        total = 0
        for i, digit in enumerate(reversed(digits)):
            total += int(digit) * factors[i % len(factors)]
        mod = 11 - (total % 11)
        dv = '0' if mod == 11 else 'K' if mod == 10 else str(mod)
        return f"{digits}-{dv}"

    def _reset_demo_data(self, company_ruts: list[str], usernames: list[str]):
        self.stdout.write('Limpiando datos previos...')
        Company.objects.filter(rut__in=company_ruts).delete()
        CartItem.objects.filter(user__username__in=usernames).delete()
        get_user_model().objects.filter(username__in=usernames).delete()

    def _ensure_seed_plans(self):
        feature_specs = {
            'inventory': 'Inventario y compras',
            'sales': 'Ventas y órdenes',
            'orders': 'Checkout',
            'pos': 'POS',
            'reports': 'Reportes',
            'user_management': 'Gestión de usuarios',
            'branches_unlimited': 'Sucursales ilimitadas',
        }
        features = {}
        for code, label in feature_specs.items():
            feature, _ = PlanFeature.objects.get_or_create(code=code, defaults={'label': label})
            features[code] = feature

        plan_specs = [
            ('BASICO', 'Plan Básico', 1, ['inventory', 'sales', 'orders', 'pos', 'user_management']),
            ('ESTANDAR', 'Plan Estándar', 3, ['inventory', 'sales', 'orders', 'pos', 'reports', 'user_management']),
            ('PREMIUM', 'Plan Premium', None, ['inventory', 'sales', 'orders', 'pos', 'reports', 'user_management', 'branches_unlimited']),
        ]
        for code, name, branch_limit, feature_codes in plan_specs:
            plan, _ = Plan.objects.get_or_create(code=code, defaults={'name': name, 'branch_limit': branch_limit, 'monthly_price': 0})
            plan.name = name
            plan.branch_limit = branch_limit
            plan.is_active = True
            plan.save()
            plan.features.set([features[fc] for fc in feature_codes])

    def _ensure_super_admin(self, User):
        user, _ = User.objects.get_or_create(
            username='superadmin',
            defaults={
                'email': 'superadmin@example.com',
                'rut': '99999999-9',
                'role': User.ROLE_SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        user.role = User.ROLE_SUPER_ADMIN
        user.email = 'superadmin@example.com'
        user.rut = '99999999-9'
        user.is_staff = True
        user.is_superuser = True
        user.set_password('demo12345')
        user.save()
        return user

    def _ensure_company(self, name: str, rut: str) -> Company:
        company, _ = Company.objects.get_or_create(rut=rut, defaults={'name': name})
        if company.name != name:
            company.name = name
            company.save(update_fields=['name'])
        return company

    def _ensure_subscription(self, company: Company, plan_code: str | None = None):
        plan = Plan.objects.get(code=plan_code or 'PREMIUM')
        Subscription.objects.update_or_create(
            company=company,
            defaults={
                'plan': plan,
                'start_date': timezone.now().date(),
                'end_date': timezone.now().date() + timedelta(days=365),
                'status': Subscription.STATUS_ACTIVE,
                'canceled_at': None,
            },
        )

    def _ensure_users(self, User, company: Company) -> dict:
        users = {}
        user_specs = [
            ('ana.rios', User.ROLE_ADMIN_CLIENTE, 'ana.rios@andes.cl', self._rut_with_dv(12543218)),
            ('matias.urrutia', User.ROLE_GERENTE, 'matias.urrutia@andes.cl', self._rut_with_dv(13245768)),
            ('carlos.fuentes', User.ROLE_VENDEDOR, 'carlos.fuentes@andes.cl', self._rut_with_dv(14598237)),
        ]
        for username, role, email, rut in user_specs:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'rut': rut,
                    'role': role,
                    'company': company,
                },
            )
            user.role = role
            user.company = company
            user.email = email
            user.rut = rut
            user.set_password('demo12345')
            user.save()
            users[role.split('_')[-1] if role != User.ROLE_ADMIN_CLIENTE else 'admin_cliente'] = user
        return {'admin_cliente': users.get('admin_cliente'), 'gerente': users.get('gerente'), 'vendedor': users.get('vendedor')}

    def _ensure_additional_companies(self, User, specs):
        created = []
        for spec in specs:
            company_name, rut, plan_code = spec['company']
            company = self._ensure_company(company_name, rut)
            self._ensure_subscription(company, plan_code)
            users = []
            for username, role, email, user_rut in spec['users']:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'rut': user_rut,
                        'role': role,
                        'company': company,
                    },
                )
                user.role = role
                user.company = company
                user.email = email
                user.rut = user_rut
                user.set_password('demo12345')
                user.save()
                users.append(user)
            created.append({
                'company': company,
                'users': self._group_users_by_role(users),
                'plan_code': plan_code,
            })
        return created

    def _group_users_by_role(self, users):
        grouped = {'admin_cliente': None, 'gerente': None, 'vendedor': None}
        for user in users:
            if user.role == user.ROLE_ADMIN_CLIENTE:
                grouped['admin_cliente'] = user
            elif user.role == user.ROLE_GERENTE:
                grouped['gerente'] = user
            elif user.role == user.ROLE_VENDEDOR:
                grouped['vendedor'] = user
        return grouped

    def _seed_additional_company_data(self, spec, options):
        company = spec['company']
        users = spec['users']
        branches = self._ensure_branches(company, max(2, options['branches'] // 2))
        products = self._ensure_products(company, max(40, options['products'] // 3))
        suppliers = self._ensure_suppliers(company, max(10, options['suppliers'] // 3))

        inventory_cache = self._seed_inventories(company, branches, products)
        purchaser = users.get('gerente') or users.get('admin_cliente')
        seller = users.get('vendedor') or purchaser

        demo_options = options | {
            'purchases': max(30, options['purchases'] // 2),
            'sales': max(60, options['sales'] // 2),
            'orders': max(40, options['orders'] // 3),
        }
        if purchaser:
            self._create_purchases(company, branches, suppliers, products, inventory_cache, purchaser, demo_options)
        if seller:
            self._create_sales(company, branches, products, inventory_cache, seller, demo_options)
        self._create_orders(company, branches, products, inventory_cache, demo_options)
        if seller:
            self._create_cart_items(seller, products)

        Inventory.objects.bulk_update(list(inventory_cache.values()), ['stock', 'reorder_point'])

    def _ensure_branches(self, company: Company, target: int) -> list[Branch]:
        names = [
            ('Casa Matriz', 'Av. Providencia 1200, Santiago'),
            ('Sucursal Norte', 'Av. Recoleta 345, Concepción'),
            ('Sucursal Sur', 'Camino a Melipilla 890, Talca'),
            ('Sucursal Oriente', 'Av. La Dehesa 450, Lo Barnechea'),
            ('Sucursal Poniente', 'Av. Pajaritos 950, Maipú'),
            ('Sucursal Centro', 'Moneda 987, Santiago Centro'),
        ]
        branches = []
        for idx in range(target):
            base_name, address = names[idx % len(names)]
            name = base_name if idx < len(names) else f"{base_name} {idx + 1}"
            branch, _ = Branch.objects.update_or_create(
                company=company,
                name=name,
                defaults={
                    'address': address,
                    'phone': f'+56 9 5555 0{idx:03d}',
                },
            )
            branches.append(branch)
        return branches

    def _ensure_products(self, company: Company, target: int) -> list[Product]:
        rng = random.Random(42)
        categories = ['Electrónica', 'Oficina', 'Hogar', 'Outdoor', 'Computación', 'Deportes', 'Belleza']
        name_pool = [
            'Audífonos inalámbricos',
            'Mouse ergonómico',
            'Teclado mecánico',
            'Silla gamer',
            'Monitor ultrawide',
            'SSD portátil',
            'Impresora láser',
            'Cafetera programable',
            'Lámpara de escritorio LED',
            'Botella térmica',
            'Mochila para notebook',
            'Parlante bluetooth',
            'Cámara web HD',
            'Router WiFi 6',
            'Organizador de cables',
            'Kit destornilladores de precisión',
            'Soporte para monitor',
            'Base refrigerante para laptop',
            'Libreta de notas premium',
            'Bolígrafo de acero',
        ]

        existing_skus = set(
            Product.objects.filter(company=company).values_list('sku', flat=True)
        )
        products_to_create = []
        for i in range(1, target + 1):
            sku = f'SKU-{i:05d}'
            if sku in existing_skus:
                continue
            price = Decimal(rng.randint(5000, 90000))
            cost = (price * Decimal('0.6')).quantize(Decimal('0.01'))
            base_name = name_pool[(i - 1) % len(name_pool)]
            suffix = f" #{(i - 1) // len(name_pool) + 1}" if i > len(name_pool) else ''
            name = f"{base_name}{suffix}"
            products_to_create.append(
                Product(
                    company=company,
                    sku=sku,
                    name=name,
                    description=f'{name} - artículo de demostración',
                    price=price,
                    cost=cost,
                    category=rng.choice(categories),
                )
            )
        if products_to_create:
            Product.objects.bulk_create(products_to_create)
        return list(Product.objects.filter(company=company))

    def _ensure_suppliers(self, company: Company, target: int) -> list[Supplier]:
        rng = random.Random(99)
        existing_ruts = set(
            Supplier.objects.filter(company=company).values_list('rut', flat=True)
        )
        supplier_pool = [
            ('Ferretería Los Héroes', 'Paula Martínez', 'compras@losheroes.cl'),
            ('Distribuidora Austral', 'Sebastián Rojas', 'ventas@daustral.cl'),
            ('Importadora Ñuñoa', 'Claudia Pizarro', 'contacto@importnunoa.cl'),
            ('AgroChile Proveedores', 'Ignacio Bravo', 'ibravo@agrochile.cl'),
            ('ServiRed Eléctrica', 'Valentina Correa', 'vcorrea@servired.cl'),
            ('Maderas San Joaquín', 'Felipe Araya', 'faraya@maderassj.cl'),
            ('Plásticos del Pacífico', 'Daniela Silva', 'dsilva@plaspacifico.cl'),
            ('Textiles Maipo', 'Lorena Carrasco', 'lcarrasco@tmaipo.cl'),
            ('Lácteos del Sur', 'Tomás Quiroz', 'tquiroz@lacteosur.cl'),
            ('CobreAndes Insumos', 'Camila Vergara', 'cvergara@cobreandes.cl'),
        ]
        suppliers_to_create = []
        for i in range(target):
            rut = self._rut_with_dv(80020000 + i)
            if rut in existing_ruts:
                continue
            name, contact, email = supplier_pool[i % len(supplier_pool)]
            suppliers_to_create.append(
                Supplier(
                    company=company,
                    name=name,
                    rut=rut,
                    contact_name=contact,
                    contact_email=email,
                    contact_phone=f'+56 9 {rng.randint(30000000, 99999999)}',
                )
            )
        if suppliers_to_create:
            Supplier.objects.bulk_create(suppliers_to_create)
        return list(Supplier.objects.filter(company=company))

    def _seed_inventories(self, company: Company, branches: list[Branch], products: list[Product]) -> dict:
        rng = random.Random(123)
        existing = Inventory.objects.filter(company=company).select_related('branch', 'product')
        cache = {(inv.branch_id, inv.product_id): inv for inv in existing}
        to_create = []
        for branch in branches:
            for product in products:
                stock = rng.randint(80, 400)
                reorder = rng.randint(10, 60)
                key = (branch.id, product.id)
                if key in cache:
                    inv = cache[key]
                    inv.stock = stock
                    inv.reorder_point = reorder
                else:
                    inv = Inventory(
                        company=company,
                        branch=branch,
                        product=product,
                        stock=stock,
                        reorder_point=reorder,
                    )
                    cache[key] = inv
                    to_create.append(inv)
        if to_create:
            Inventory.objects.bulk_create(to_create)
        return cache

    def _create_purchases(self, company, branches, suppliers, products, inventory_cache, created_by, options):
        rng = random.Random(501)
        purchase_items = []
        movements = []
        purchase_count = options['purchases']
        items_per_purchase = max(1, options['items_per_purchase'])
        for _ in range(purchase_count):
            branch = rng.choice(branches)
            supplier = rng.choice(suppliers)
            purchase = Purchase.objects.create(
                company=company,
                branch=branch,
                supplier=supplier,
                date=timezone.now().date() - timedelta(days=rng.randint(0, 15)),
                created_by=created_by,
                total_cost=0,
            )
            total_cost = Decimal('0')
            chosen_products = rng.sample(products, k=min(items_per_purchase, len(products)))
            for product in chosen_products:
                quantity = rng.randint(5, 25)
                unit_cost = (product.cost * Decimal(rng.uniform(0.9, 1.2))).quantize(Decimal('0.01'))
                inv = inventory_cache[(branch.id, product.id)]
                inv.stock += quantity
                total_cost += unit_cost * quantity
                purchase_items.append(
                    PurchaseItem(
                        purchase=purchase,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                    )
                )
                movements.append(
                    InventoryMovement(
                        company=company,
                        branch=branch,
                        product=product,
                        movement_type=InventoryMovement.MOV_PURCHASE,
                        quantity_delta=quantity,
                        reason='Compra demo',
                        created_by=created_by,
                    )
                )
            purchase.total_cost = total_cost
            purchase.save(update_fields=['total_cost'])
        if purchase_items:
            PurchaseItem.objects.bulk_create(purchase_items)
        if movements:
            InventoryMovement.objects.bulk_create(movements)

    def _create_sales(self, company, branches, products, inventory_cache, seller, options):
        rng = random.Random(901)
        sale_items = []
        movements = []
        branch_map = {}
        for inv in inventory_cache.values():
            branch_map.setdefault(inv.branch_id, []).append(inv)
        sales_created = []
        sale_count = options['sales']
        items_per_sale = max(1, options['items_per_sale'])
        for _ in range(sale_count):
            branch = rng.choice(branches)
            sale = Sale.objects.create(
                company=company,
                branch=branch,
                seller=seller,
                payment_method=rng.choice(['Efectivo', 'Débito', 'Crédito']),
                total=0,
            )
            total_sale = Decimal('0')
            created_items = 0
            for _ in range(items_per_sale):
                candidates = [inv for inv in branch_map.get(branch.id, []) if inv.stock > 0]
                if not candidates:
                    break
                inv = rng.choice(candidates)
                quantity = rng.randint(1, min(inv.stock, 6))
                if quantity <= 0:
                    continue
                inv.stock -= quantity
                unit_price = inv.product.price
                total_sale += unit_price * quantity
                sale_items.append(
                    SaleItem(
                        sale=sale,
                        product=inv.product,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                )
                movements.append(
                    InventoryMovement(
                        company=company,
                        branch=branch,
                        product=inv.product,
                        movement_type=InventoryMovement.MOV_SALE,
                        quantity_delta=-quantity,
                        reason='Venta demo',
                        created_by=seller,
                    )
                )
                created_items += 1
            if created_items == 0:
                sale.delete()
            else:
                sale.total = total_sale
                sale.save(update_fields=['total'])
                sales_created.append(sale)
        if sale_items:
            SaleItem.objects.bulk_create(sale_items)
        if movements:
            InventoryMovement.objects.bulk_create(movements)

    def _create_orders(self, company, branches, products, inventory_cache, options):
        rng = random.Random(777)
        order_items = []
        movements = []
        branch_map = {}
        for inv in inventory_cache.values():
            branch_map.setdefault(inv.branch_id, []).append(inv)
        orders_created = []
        order_count = options['orders']
        items_per_order = max(1, options['items_per_order'])
        status_choices = [
            (Order.STATUS_PENDING, 60),
            (Order.STATUS_SHIPPED, 25),
            (Order.STATUS_DELIVERED, 15),
        ]
        weighted_statuses = [status for status, weight in status_choices for _ in range(weight)]
        for _ in range(order_count):
            branch = rng.choice(branches)
            order = Order.objects.create(
                company=company,
                branch=branch,
                customer_name=f'Cliente {rng.randint(1000, 9999)}',
                customer_email=f'cliente{rng.randint(1, order_count)}@demo.cl',
                status=rng.choice(weighted_statuses),
                total=0,
            )
            total_order = Decimal('0')
            created_items = 0
            for _ in range(items_per_order):
                candidates = [inv for inv in branch_map.get(branch.id, []) if inv.stock > 0]
                if not candidates:
                    break
                inv = rng.choice(candidates)
                quantity = rng.randint(1, min(inv.stock, 5))
                if quantity <= 0:
                    continue
                inv.stock -= quantity
                unit_price = inv.product.price
                total_order += unit_price * quantity
                order_items.append(
                    OrderItem(
                        order=order,
                        product=inv.product,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                )
                movements.append(
                    InventoryMovement(
                        company=company,
                        branch=branch,
                        product=inv.product,
                        movement_type=InventoryMovement.MOV_SALE,
                        quantity_delta=-quantity,
                        reason='Orden demo',
                    )
                )
                created_items += 1
            if created_items == 0:
                order.delete()
            else:
                order.total = total_order
                order.save(update_fields=['total'])
                orders_created.append(order)
        if order_items:
            OrderItem.objects.bulk_create(order_items)
        if movements:
            InventoryMovement.objects.bulk_create(movements)

    def _create_cart_items(self, vendor, products):
        rng = random.Random(333)
        CartItem.objects.filter(user=vendor).delete()
        cart_items = []
        sample_size = min(len(products), rng.randint(10, 25))
        for product in rng.sample(products, k=sample_size):
            cart_items.append(
                CartItem(
                    user=vendor,
                    product=product,
                    quantity=rng.randint(1, 3),
                )
            )
        if cart_items:
            CartItem.objects.bulk_create(cart_items, ignore_conflicts=True)

    def _print_summary(self, company: Company, usernames: list[str], super_admin, extra_companies):
        inventory_rows = Inventory.objects.filter(company=company).count()
        purchases = Purchase.objects.filter(company=company).count()
        purchase_items = PurchaseItem.objects.filter(purchase__company=company).count()
        sales = Sale.objects.filter(company=company).count()
        sale_items = SaleItem.objects.filter(sale__company=company).count()
        orders = Order.objects.filter(company=company).count()
        order_items = OrderItem.objects.filter(order__company=company).count()
        branches = Branch.objects.filter(company=company).count()
        products = Product.objects.filter(company=company).count()
        suppliers = Supplier.objects.filter(company=company).count()

        self.stdout.write(self.style.SUCCESS('Datos de demo creados/actualizados'))
        self.stdout.write(f'Company: {company.id} - {company.name} ({company.rut}) Plan: {company.subscription.plan.name}')
        self.stdout.write(f'Sucursales: {branches}, Productos: {products}, Proveedores: {suppliers}')
        self.stdout.write(f'Inventario: {inventory_rows} filas')
        self.stdout.write(f'Compras: {purchases} con {purchase_items} items')
        self.stdout.write(f'Ventas: {sales} con {sale_items} items')
        self.stdout.write(f'Órdenes: {orders} con {order_items} items')
        top_low_stock = (
            Inventory.objects.filter(company=company)
            .select_related('product', 'branch')
            .order_by('stock')[:5]
        )
        self.stdout.write('Productos con menor stock:')
        for inv in top_low_stock:
            self.stdout.write(
                f"- {inv.product.name} / {inv.branch.name}: stock {inv.stock}, reorder {inv.reorder_point}"
            )
        self.stdout.write('Usuarios demo:')
        for username in usernames:
            self.stdout.write(f'- {username} / demo12345')
        self.stdout.write('')
        self.stdout.write(f'Superadmin: {super_admin.username} / demo12345')
        self.stdout.write('Cuentas en otros planes:')
        for extra_company in extra_companies:
            company_obj = extra_company['company']
            users = [u for u in extra_company['users'].values() if u]
            plan = company_obj.subscription.plan.name if hasattr(company_obj, 'subscription') else 'SIN PLAN'
            self.stdout.write(f'- {company_obj.name} ({plan})')
            for user in users:
                self.stdout.write(f"  * {user.username} ({user.get_role_display()}) / demo12345")
