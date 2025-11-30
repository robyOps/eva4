from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from apps.core.permissions import IsActive, CompanyPlanAllowsReports
from apps.inventory.models import Inventory, Branch
from apps.sales.models import Sale


class StockReportView(APIView):
    permission_classes = [IsActive, CompanyPlanAllowsReports]

    def get(self, request):
        branch_id = request.query_params.get('branch')
        qs = Inventory.objects.filter(company=request.user.company)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        data = list(qs.values('branch__name', 'product__name', 'stock'))
        return Response(data)


class SalesReportView(APIView):
    permission_classes = [IsActive, CompanyPlanAllowsReports]

    def get(self, request):
        branch_id = request.query_params.get('branch')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        group = request.query_params.get('group', 'day')
        qs = Sale.objects.filter(company=request.user.company)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        annotator = TruncDay('created_at') if group == 'day' else TruncMonth('created_at')
        qs = qs.annotate(period=annotator).values('period').annotate(total=Sum('total')).order_by('period')
        return Response(qs)
