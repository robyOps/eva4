from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from decimal import Decimal

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.inventory.models import Branch, Inventory, Product, Supplier
from apps.inventory.web_views import _guard_role
from apps.sales.models import CartItem, Order, Sale


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

    context = {
        'company': company,
        'kpis': {
            'products': products.count(),
            'suppliers': suppliers.count(),
            'branches': branches.count(),
            'inventory_rows': inventories.count(),
            'low_stock': low_stock.count(),
            'sales_today': sales_today.count(),
            'pending_orders': pending_orders.count(),
        },
        'has_data': products.exists() or suppliers.exists() or inventories.exists(),
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
    context = {
        'cart_lines': cart_lines,
        'branches': branches,
        'total': total,
        'has_items': bool(cart_lines),
    }
    return render(request, 'shop/checkout.html', context)


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
    if request.method == 'POST':
        data = {
            'username': request.POST.get('username', ''),
            'email': request.POST.get('email', ''),
            'password': request.POST.get('password', ''),
            'role': request.POST.get('role'),
            'rut': request.POST.get('rut', ''),
        }
        serializer = UserSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            messages.success(request, 'Usuario creado correctamente')
            return redirect('dashboard')
        errors = serializer.errors

    return render(request, 'users/create.html', {'errors': errors})
