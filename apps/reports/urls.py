from django.urls import path
from .views import StockReportView, SalesReportView

urlpatterns = [
    path('reports/stock/', StockReportView.as_view(), name='report-stock'),
    path('reports/sales/', SalesReportView.as_view(), name='report-sales'),
]
