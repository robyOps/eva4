from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.models import User
from apps.inventory.models import Branch, Inventory, Supplier
from apps.inventory.web_views import _guard_role
from django.db.models import Count, Max


@login_required
def stock_report(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    company = request.user.company
    subscription = getattr(company, 'subscription', None)
    reports_enabled = bool(subscription and subscription.reports_enabled and subscription.active)
    if not reports_enabled:
        messages.warning(request, 'Tu plan no permite ver reportes de stock. Mejora el plan para habilitarlos.')

    branches = Branch.objects.filter(company=company).order_by('name')
    selected_branch_id = request.GET.get('branch')
    inventories = Inventory.objects.filter(company=company).select_related('product', 'branch').order_by('product__name')
    if selected_branch_id:
        inventories = inventories.filter(branch_id=selected_branch_id)

    context = {
        'inventories': inventories if reports_enabled else [],
        'branches': branches,
        'selected_branch_id': selected_branch_id,
        'reports_enabled': reports_enabled,
    }
    return render(request, 'reports/stock.html', context)


@login_required
def suppliers_report(request):
    denial = _guard_role(request, {User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_SUPER_ADMIN})
    if denial:
        return denial

    company = request.user.company
    subscription = getattr(company, 'subscription', None)
    reports_enabled = bool(subscription and subscription.reports_enabled and subscription.active)
    if not reports_enabled:
        messages.warning(request, 'Tu plan no permite ver reportes de proveedores. Mejora el plan para habilitarlos.')

    suppliers = Supplier.objects.filter(company=company).annotate(
        total_purchases=Count('purchase', distinct=True),
        last_purchase=Max('purchase__date'),
        products_count=Count('purchase__items__product', distinct=True),
    ).order_by('name') if reports_enabled else Supplier.objects.none()

    context = {
        'suppliers': suppliers,
        'reports_enabled': reports_enabled,
    }
    return render(request, 'reports/suppliers.html', context)
