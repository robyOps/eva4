from django.urls import path
from .views import StockReportView, SalesReportView, SupplierReportView

urlpatterns = [
    path('reports/stock/', StockReportView.as_view(), name='report-stock'),
    path('reports/sales/', SalesReportView.as_view(), name='report-sales'),
    path('reports/suppliers/', SupplierReportView.as_view(), name='report-suppliers'),
]
