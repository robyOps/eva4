from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum

from apps.accounts.models import User
from apps.inventory.models import Branch, Product
from apps.inventory.web_views import _guard_role
from .models import Sale
from .serializers import SaleSerializer
from .services import create_sale


@login_required
def sales_list(request):
    allowed_roles = {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN, User.ROLE_VENDEDOR}
    denial = _guard_role(request, allowed_roles)
    if denial:
        return denial

    company = request.user.company
    branches = Branch.objects.filter(company=company).order_by('name')
    branch_id = request.GET.get('branch')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    qs = Sale.objects.filter(company=company)
    if request.user.role == User.ROLE_VENDEDOR:
        qs = qs.filter(seller=request.user)

    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, f'Fecha inválida: {value}')
            return None

    date_from_parsed = parse_date(date_from)
    date_to_parsed = parse_date(date_to)
    if date_from_parsed:
        qs = qs.filter(created_at__date__gte=date_from_parsed)
    if date_to_parsed:
        qs = qs.filter(created_at__date__lte=date_to_parsed)

    sales = qs.select_related('branch', 'seller').annotate(item_count=Sum('items__quantity')).order_by('-created_at')

    context = {
        'sales': sales,
        'branches': branches,
        'selected_branch_id': branch_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'sales/list.html', context)


@login_required
def pos_new_sale(request):
    allowed_roles = {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_VENDEDOR, User.ROLE_SUPER_ADMIN}
    denial = _guard_role(request, allowed_roles)
    if denial:
        return denial

    company = request.user.company
    branches = Branch.objects.filter(company=company).order_by('name')
    products = Product.objects.filter(company=company).order_by('name')
    form_errors = []
    item_rows = []
    selected_branch_id = None
    payment_method_value = 'Efectivo'

    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        selected_branch_id = branch_id
        payment_method = request.POST.get('payment_method') or 'Efectivo'
        payment_method_value = payment_method
        product_ids = request.POST.getlist('product[]') or request.POST.getlist('item_product')
        quantities = request.POST.getlist('quantity[]') or request.POST.getlist('item_quantity')

        items = []
        for idx, (pid, qty) in enumerate(zip(product_ids, quantities), start=1):
            pid = (pid or '').strip()
            qty = (qty or '').strip()
            if not pid and not qty:
                continue
            if not pid or not qty:
                form_errors.append(f'Fila {idx}: indica producto y cantidad.')
                item_rows.append({'product_id': pid, 'quantity': qty or '1'})
                continue
            try:
                quantity_int = int(qty)
                if quantity_int < 1:
                    raise ValueError
            except ValueError:
                form_errors.append(f'Fila {idx}: cantidad inválida (mínimo 1).')
                item_rows.append({'product_id': pid, 'quantity': qty or '1'})
                continue
            try:
                product = products.get(pk=pid)
            except Product.DoesNotExist:
                form_errors.append(f'Fila {idx}: producto inválido.')
                item_rows.append({'product_id': pid, 'quantity': qty or '1'})
                continue
            item_rows.append({'product_id': str(product.id), 'quantity': str(quantity_int)})
            items.append({'product': product.id, 'quantity': quantity_int, 'unit_price': str(product.price)})

        data = {
            'branch': branch_id,
            'payment_method': payment_method,
            'items': items,
        }

        serializer = SaleSerializer(data=data, context={'request': request})
        if serializer.is_valid() and not form_errors:
            try:
                sale = create_sale(serializer.validated_data, request.user)
                messages.success(request, f'Venta #{sale.id} registrada correctamente')
                return redirect('sales_list')
            except Exception as exc:
                form_errors.append(str(getattr(exc, 'detail', exc)))
        else:
            form_errors.extend([f"{key}: {', '.join(map(str, val))}" for key, val in serializer.errors.items()])

    if not item_rows:
        item_rows.append({'product_id': '', 'quantity': '1'})

    return render(request, 'sales/pos.html', {
        'branches': branches,
        'products': products,
        'form_errors': form_errors,
        'item_rows': item_rows,
        'selected_branch_id': selected_branch_id,
        'payment_method_value': payment_method_value,
    })
