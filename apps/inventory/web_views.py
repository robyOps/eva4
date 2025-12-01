from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db import transaction
from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from .forms import SupplierForm, BranchForm
from .models import Branch, Inventory, Supplier, Product, Purchase, PurchaseItem, InventoryMovement
from .serializers import PurchaseSerializer


def _user_has_role(user, allowed_roles):
    user_role = getattr(user, 'role', None)
    return bool(user and user.is_authenticated and (user_role in allowed_roles or user.is_superuser))


def _guard_role(request, allowed_roles):
    if not _user_has_role(request.user, allowed_roles):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    if getattr(request.user, 'role', None) == User.ROLE_SUPER_ADMIN:
        return None
    if not request.user.company:
        messages.error(request, 'Debes pertenecer a una compañía para ver esta sección.')
        return redirect('dashboard')
    return None


@login_required
def suppliers_list(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial
    suppliers = Supplier.objects.filter(company=request.user.company).order_by('name')
    context = {
        'suppliers': suppliers,
        'can_create': _user_has_role(request.user, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN}),
    }
    return render(request, 'suppliers/list.html', context)


@login_required
def supplier_create(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial
    if request.method == 'POST':
        form = SupplierForm(request.POST, company=request.user.company)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.company = request.user.company
            supplier.save()
            messages.success(request, 'Proveedor creado correctamente')
            return redirect('suppliers_list')
    else:
        form = SupplierForm(company=request.user.company)
    return render(request, 'suppliers/create.html', {'form': form})


@login_required
def branches_list(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial
    branches = Branch.objects.filter(company=request.user.company).order_by('name')
    return render(request, 'branches/list.html', {'branches': branches})


@login_required
def branch_create(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    subscription = getattr(request.user.company, 'subscription', None)
    branch_limit = getattr(subscription, 'branch_limit', None)
    current_count = Branch.objects.filter(company=request.user.company).count()
    if branch_limit and current_count >= branch_limit:
        messages.warning(request, 'Límite de sucursales alcanzado para tu plan. Mejora el plan para crear más.')
        return redirect('branches_list')

    if request.method == 'POST':
        form = BranchForm(request.POST, company=request.user.company)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.company = request.user.company
            branch.save()
            messages.success(request, 'Sucursal creada correctamente')
            return redirect('branches_list')
    else:
        form = BranchForm(company=request.user.company)
    return render(request, 'branches/create.html', {'form': form, 'branch_limit': branch_limit, 'current_count': current_count})


@login_required
def inventory_by_branch(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN, User.ROLE_VENDEDOR})
    if denial:
        return denial
    branches = Branch.objects.filter(company=request.user.company).order_by('name')
    selected_branch_id = request.GET.get('branch')
    selected_branch = None
    if selected_branch_id:
        selected_branch = branches.filter(id=selected_branch_id).first()
    if not selected_branch and branches:
        selected_branch = branches[0]

    inventories = Inventory.objects.filter(company=request.user.company)
    if selected_branch:
        inventories = inventories.filter(branch=selected_branch)
    inventories = inventories.select_related('product', 'branch').order_by('product__name')

    context = {
        'branches': branches,
        'selected_branch': selected_branch,
        'inventories': inventories,
    }
    return render(request, 'inventory/branch_inventory.html', context)


def _create_purchase(validated_data, user):
    items_data = validated_data.pop('items')
    branch = validated_data['branch']
    supplier = validated_data['supplier']
    if branch.company != user.company or supplier.company != user.company:
        raise ValidationError('Sucursal o proveedor inválido para esta compañía')
    purchase = Purchase.objects.create(company=user.company, created_by=user, **validated_data)
    total = 0
    with transaction.atomic():
        for item in items_data:
            product = item['product']
            quantity = item['quantity']
            unit_cost = item['unit_cost']
            total += quantity * unit_cost
            PurchaseItem.objects.create(purchase=purchase, **item)
            inventory, _ = Inventory.objects.get_or_create(
                company=user.company,
                branch=purchase.branch,
                product=product,
                defaults={'stock': 0},
            )
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


@login_required
def purchase_create(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    company = request.user.company
    branches = Branch.objects.filter(company=company).order_by('name')
    suppliers = Supplier.objects.filter(company=company).order_by('name')
    products = Product.objects.filter(company=company).order_by('name')
    form_errors = []
    items_payload = []

    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        supplier_id = request.POST.get('supplier')
        date_input = request.POST.get('date') or timezone.now().date()
        product_ids = request.POST.getlist('item_product')
        quantities = request.POST.getlist('item_quantity')
        costs = request.POST.getlist('item_unit_cost')

        items = []
        for idx, (pid, qty, cost) in enumerate(zip(product_ids, quantities, costs), start=1):
            if not pid and not qty:
                continue
            if not pid or not qty:
                form_errors.append(f'Fila {idx}: indica producto y cantidad.')
                continue
            try:
                qty_int = int(qty)
                if qty_int < 1:
                    raise ValueError
            except ValueError:
                form_errors.append(f'Fila {idx}: cantidad inválida (mínimo 1).')
                continue
            try:
                unit_cost = Decimal(cost or '0')
                if unit_cost < 0:
                    raise InvalidOperation
            except InvalidOperation:
                form_errors.append(f'Fila {idx}: costo unitario inválido.')
                continue
            items.append({'product': pid, 'quantity': qty_int, 'unit_cost': str(unit_cost)})
            items_payload.append({'product': pid, 'quantity': qty_int, 'unit_cost': unit_cost})

        data = {
            'branch': branch_id,
            'supplier': supplier_id,
            'date': date_input,
            'items': items,
        }
        serializer = PurchaseSerializer(data=data)
        if serializer.is_valid() and not form_errors:
            try:
                purchase = _create_purchase(serializer.validated_data, request.user)
                messages.success(request, f'Compra #{purchase.id} creada correctamente.')
                return redirect('purchase_create')
            except ValidationError as exc:
                form_errors.append(str(getattr(exc, 'detail', exc)))
        else:
            form_errors.extend([f"{key}: {', '.join(map(str, val))}" for key, val in serializer.errors.items()])

    context = {
        'branches': branches,
        'suppliers': suppliers,
        'products': products,
        'form_errors': form_errors,
        'selected_branch_id': request.POST.get('branch') if request.method == 'POST' else None,
        'selected_supplier_id': request.POST.get('supplier') if request.method == 'POST' else None,
        'date_value': request.POST.get('date') if request.method == 'POST' else timezone.now().date(),
        'items_payload': items_payload,
    }
    return render(request, 'purchases/create.html', context)
