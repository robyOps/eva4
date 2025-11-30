from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Branch, Inventory, InventoryMovement, Product, Supplier
from apps.inventory.web_views import _guard_role
from apps.sales.models import CartItem, Order, OrderItem, Sale


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Credenciales inválidas, intenta nuevamente o usa el botón de JWT con tu usuario y contraseña.')
    return render(request, 'login.html')


@login_required
def dashboard(request):
    company = getattr(request.user, 'company', None)
    if not company:
        context = {'missing_company': True}
        return render(request, 'dashboard.html', context)

    products = Product.objects.filter(company=company)
    suppliers = Supplier.objects.filter(company=company)
    branches = Branch.objects.filter(company=company)
    inventories = Inventory.objects.filter(company=company)
    low_stock = inventories.filter(stock__lte=F('reorder_point'))

    today = timezone.now().date()
    sales_today = Sale.objects.filter(company=company, created_at__date=today)
    pending_orders = Order.objects.filter(company=company, status=Order.STATUS_PENDING)

    role = request.user.role
    has_data = products.exists() or suppliers.exists() or inventories.exists()

    if role == User.ROLE_VENDEDOR:
        kpis = [
            {'title': 'Productos disponibles', 'value': products.count()},
            {'title': 'Ítems en carrito', 'value': CartItem.objects.filter(user=request.user, product__company=company).count()},
            {'title': 'Mis ventas', 'value': Sale.objects.filter(company=company, seller=request.user).count()},
            {'title': 'Órdenes pendientes', 'value': pending_orders.count()},
        ]
        quick_actions = [
            {'label': 'Productos', 'url': 'shop-products'},
            {'label': 'Carro', 'url': 'shop-cart'},
            {'label': 'POS', 'url': 'pos_new_sale'},
            {'label': 'Mis órdenes', 'url': 'shop_orders'},
        ]
    elif role == User.ROLE_GERENTE:
        kpis = [
            {'title': 'Productos', 'value': products.count()},
            {'title': 'Proveedores', 'value': suppliers.count()},
            {'title': 'Stock bajo', 'value': low_stock.count()},
            {'title': 'Ventas de hoy', 'value': sales_today.count()},
            {'title': 'Órdenes pendientes', 'value': pending_orders.count()},
        ]
        quick_actions = [
            {'label': 'Inventario', 'url': 'inventory_by_branch'},
            {'label': 'Proveedores', 'url': 'suppliers_list'},
            {'label': 'Reportes', 'url': 'report_stock'},
            {'label': 'Ventas', 'url': 'sales_list'},
        ]
    else:
        kpis = [
            {'title': 'Productos', 'value': products.count()},
            {'title': 'Proveedores', 'value': suppliers.count()},
            {'title': 'Sucursales', 'value': branches.count()},
            {'title': 'Stock bajo', 'value': low_stock.count()},
            {'title': 'Ventas de hoy', 'value': sales_today.count()},
            {'title': 'Órdenes pendientes', 'value': pending_orders.count()},
        ]
        quick_actions = [
            {'label': 'Sucursales', 'url': 'branches_list'},
            {'label': 'Usuarios', 'url': 'user_create'},
            {'label': 'Suscripción', 'url': 'subscription_detail'},
            {'label': 'Ventas', 'url': 'sales_list'},
        ]

    context = {
        'company': company,
        'kpis': kpis,
        'quick_actions': quick_actions,
        'role': role,
        'has_data': has_data,
    }
    return render(request, 'dashboard.html', context)


@login_required
def product_list(request):
    company = getattr(request.user, 'company', None)
    products = Product.objects.none()
    if not company:
        messages.warning(request, 'Asocia el usuario a una compañía para ver el catálogo de productos.')
    else:
        products = Product.objects.filter(company=company)
        if not products.exists():
            messages.info(request, 'No hay productos disponibles. Ejecuta "python manage.py seed_demo --reset" para cargar datos de ejemplo.')
    return render(request, 'shop/products.html', {'products': products, 'company': company})


@login_required
def product_detail(request, pk):
    company = getattr(request.user, 'company', None)
    if not company:
        messages.warning(request, 'No puedes ver el detalle sin pertenecer a una compañía.')
        return redirect('shop-products')
    try:
        product = Product.objects.get(pk=pk, company=company)
    except Product.DoesNotExist as exc:
        raise Http404 from exc
    return render(request, 'shop/product_detail.html', {'product': product})


@login_required
def cart_add_view(request):
    if request.method != 'POST':
        return redirect('shop-products')

    company = getattr(request.user, 'company', None)
    if not company:
        messages.error(request, 'Asocia tu usuario a una compañía antes de usar el carrito.')
        return redirect('shop-products')

    product_id = request.POST.get('product_id') or request.POST.get('product')
    quantity_raw = request.POST.get('quantity', '1')
    try:
        quantity = int(quantity_raw)
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, 'Cantidad inválida para el carrito.')
        return redirect(request.META.get('HTTP_REFERER', 'shop-products'))

    product = get_object_or_404(Product, pk=product_id, company=company)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': quantity},
    )
    if not created:
        cart_item.quantity = quantity
        cart_item.save()
    messages.success(request, f'{product.name} agregado al carrito')
    return redirect(request.META.get('HTTP_REFERER', 'shop-products'))


@login_required
def cart_view(request):
    company = getattr(request.user, 'company', None)
    if not company:
        messages.warning(request, 'Asigna una compañía antes de gestionar tu carrito.')
        items = CartItem.objects.none()
    else:
        items = CartItem.objects.filter(user=request.user, product__company=company).select_related('product')
    cart_lines = [{'item': item, 'subtotal': item.product.price * item.quantity} for item in items]
    total = sum((line['subtotal'] for line in cart_lines), Decimal('0'))
    context = {'cart_lines': cart_lines, 'company': company, 'total': total, 'has_items': bool(cart_lines)}
    return render(request, 'shop/cart.html', context)


@login_required
def checkout_view(request):
    company = getattr(request.user, 'company', None)
    if not company:
        messages.warning(request, 'Asigna una compañía antes de confirmar el checkout.')
        return redirect('dashboard')

    items = CartItem.objects.filter(user=request.user, product__company=company).select_related('product')
    cart_lines = [{'item': item, 'subtotal': item.product.price * item.quantity} for item in items]
    branches = Branch.objects.filter(company=company)
    total = sum((line['subtotal'] for line in cart_lines), Decimal('0'))

    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        selected_branch = Branch.objects.filter(id=branch_id, company=company).first()
        if not cart_lines:
            messages.error(request, 'No hay productos en el carrito para procesar.')
            return redirect('shop-cart')
        if not selected_branch:
            messages.error(request, 'Selecciona una sucursal válida.')
        else:
            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        company=company,
                        branch=selected_branch,
                        customer_name=request.user.username or 'Cliente',
                        customer_email=request.user.email or '',
                        total=0,
                    )
                    running_total = Decimal('0')
                    for ci in items.select_for_update():
                        inventory = Inventory.objects.select_for_update().get(company=company, branch=selected_branch, product=ci.product)
                        if inventory.stock < ci.quantity:
                            raise ValidationError('Stock insuficiente para ' + ci.product.name)
                        inventory.stock -= ci.quantity
                        inventory.save()
                        price = ci.product.price
                        running_total += price * ci.quantity
                        OrderItem.objects.create(order=order, product=ci.product, quantity=ci.quantity, unit_price=price)
                        InventoryMovement.objects.create(
                            company=company,
                            branch=selected_branch,
                            product=ci.product,
                            movement_type=InventoryMovement.MOV_SALE,
                            quantity_delta=-ci.quantity,
                            reason='Checkout',
                            created_by=request.user,
                        )
                    order.total = running_total
                    order.save()
                    items.delete()
                messages.success(request, f'Orden #{order.id} creada')
                return redirect('shop_orders')
            except Exception as exc:
                detail = getattr(exc, 'detail', str(exc))
                messages.error(request, f'No se pudo crear la orden: {detail}')
        context = {
            'cart_lines': cart_lines,
            'branches': branches,
            'total': total,
            'has_items': bool(cart_lines),
            'selected_branch_id': branch_id,
        }
        return render(request, 'shop/checkout.html', context)

    context = {
        'cart_lines': cart_lines,
        'branches': branches,
        'total': total,
        'has_items': bool(cart_lines),
        'selected_branch_id': None,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def orders_list_view(request):
    company = getattr(request.user, 'company', None)
    if not company:
        messages.warning(request, 'Asocia el usuario a una compañía para ver tus órdenes.')
        orders = Order.objects.none()
    else:
        orders = Order.objects.filter(company=company).select_related('branch').order_by('-created_at')
    return render(request, 'shop/orders.html', {'orders': orders})


@login_required
def order_detail_view(request, pk):
    company = getattr(request.user, 'company', None)
    if not company:
        messages.warning(request, 'Asocia el usuario a una compañía para ver esta orden.')
        return redirect('shop_orders')
    order = get_object_or_404(
        Order.objects.select_related('branch').prefetch_related('items__product'),
        pk=pk,
        company=company,
    )
    return render(request, 'shop/order_detail.html', {'order': order})


@login_required
def tokens_view(request):
    return render(request, 'tokens.html', {'username': request.user.username})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def subscription_detail(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial
    subscription = getattr(getattr(request.user, 'company', None), 'subscription', None)
    return render(request, 'subscription/detail.html', {'subscription': subscription})


@login_required
def user_create_view(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE})
    if denial:
        return denial

    errors = []
    form_data = {
        'username': '',
        'email': '',
        'role': User.ROLE_GERENTE,
        'rut': '',
    }
    if request.method == 'POST':
        data = {
            'username': request.POST.get('username', ''),
            'email': request.POST.get('email', ''),
            'password': request.POST.get('password', ''),
            'role': request.POST.get('role'),
            'rut': request.POST.get('rut', ''),
        }
        form_data.update(data)
        serializer = UserSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            messages.success(request, 'Usuario creado correctamente')
            return redirect('dashboard')
        errors = serializer.errors

    return render(request, 'users/create.html', {'errors': errors, 'form_data': form_data})
