from datetime import timedelta
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

from apps.core.forms import PlanForm, SubscriptionAdminForm
from apps.core.models import Company, Plan, PlanFeature, Subscription
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
            if getattr(user, 'role', None) == User.ROLE_SUPER_ADMIN:
                return redirect('super_admin_dashboard')
            return redirect('dashboard')
        messages.error(request, 'Credenciales inválidas, intenta nuevamente o usa el botón de JWT con tu usuario y contraseña.')
    return render(request, 'login.html')


@login_required
def dashboard(request):
    if request.user.role == User.ROLE_SUPER_ADMIN:
        messages.info(request, 'Accede al panel de Super Admin para gestionar planes y compañías.')
        return redirect('super_admin_dashboard')

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
            {'label': 'Gestión de usuarios', 'url': 'user_create'},
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
    if request.user.role == User.ROLE_SUPER_ADMIN:
        messages.error(request, 'El super admin administra planes desde su propio panel, sin suscripciones asociadas.')
        return redirect('super_admin_dashboard')

    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE})
    if denial:
        return denial

    company = getattr(request.user, 'company', None)
    subscription = getattr(company, 'subscription', None) if company else None
    plans = Plan.objects.filter(is_active=True).prefetch_related('features').order_by('monthly_price')
    plan_features = PlanFeature.objects.filter(plans__in=plans).distinct().order_by('label')

    if request.method == 'POST':
        if not company:
            messages.error(request, 'Asocia el usuario a una compañía antes de comprar una suscripción.')
            return redirect('subscription_detail')

        plan_id = request.POST.get('plan')
        plan = get_object_or_404(plans, pk=plan_id)
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=365)
        subscription, _ = Subscription.objects.update_or_create(
            company=company,
            defaults={
                'plan': plan,
                'start_date': start_date,
                'end_date': end_date,
                'status': Subscription.STATUS_ACTIVE,
                'canceled_at': None,
            },
        )
        messages.success(request, f'Suscripción al plan {plan.name} activada automáticamente para tu compañía.')
        return redirect('subscription_detail')

    context = {
        'subscription': subscription,
        'plans': plans,
        'plan_features': plan_features,
    }
    return render(request, 'subscription/detail.html', context)


@login_required
def super_admin_dashboard(request):
    denial = _guard_role(request, {User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    companies = Company.objects.all().prefetch_related('users', 'subscription__plan')
    user_count = User.objects.count()
    active_subscriptions = Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).count()
    plan_count = Plan.objects.count()
    context = {
        'companies': companies,
        'user_count': user_count,
        'active_subscriptions': active_subscriptions,
        'plan_count': plan_count,
    }
    return render(request, 'super_admin/dashboard.html', context)


@login_required
def super_admin_plans(request):
    denial = _guard_role(request, {User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    plans = Plan.objects.prefetch_related('features').order_by('monthly_price')
    features = PlanFeature.objects.all().order_by('label')
    form = PlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Plan creado correctamente.')
        return redirect('super_admin_plans')

    context = {
        'plans': plans,
        'features': features,
        'form': form,
    }
    return render(request, 'super_admin/plans.html', context)


@login_required
def super_admin_plan_edit(request, pk):
    denial = _guard_role(request, {User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    plan = get_object_or_404(Plan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Plan actualizado correctamente.')
        return redirect('super_admin_plans')

    return render(request, 'super_admin/plan_form.html', {'form': form, 'plan': plan})


@login_required
def super_admin_plan_delete(request, pk):
    denial = _guard_role(request, {User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        if plan.subscriptions.exists():
            messages.error(request, 'No puedes eliminar un plan con suscripciones asociadas.')
        else:
            plan.delete()
            messages.success(request, 'Plan eliminado.')
        return redirect('super_admin_plans')
    return render(request, 'super_admin/plan_delete.html', {'plan': plan})


@login_required
def super_admin_subscriptions(request):
    denial = _guard_role(request, {User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    subscriptions = Subscription.objects.select_related('company', 'plan').all()
    form = SubscriptionAdminForm(request.POST or None)

    if request.method == 'POST':
        cancel_id = request.POST.get('cancel_id')
        if cancel_id:
            subscription = get_object_or_404(Subscription, pk=cancel_id)
            subscription.cancel()
            messages.success(request, f'Suscripción de {subscription.company} cancelada.')
            return redirect('super_admin_subscriptions')
        if form.is_valid():
            cleaned = form.cleaned_data
            subscription, _ = Subscription.objects.update_or_create(
                company=cleaned['company'],
                defaults={
                    'plan': cleaned['plan'],
                    'start_date': cleaned['start_date'],
                    'end_date': cleaned['end_date'],
                    'status': cleaned['status'],
                    'canceled_at': None,
                },
            )
            messages.success(request, 'Suscripción asignada/actualizada correctamente.')
            return redirect('super_admin_subscriptions')

    context = {
        'subscriptions': subscriptions,
        'form': form,
    }
    return render(request, 'super_admin/subscriptions.html', context)


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
