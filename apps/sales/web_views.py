from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum

from apps.accounts.models import User
from apps.inventory.models import Branch
from apps.inventory.web_views import _guard_role
from .models import Sale


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
