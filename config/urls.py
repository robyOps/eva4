from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.shop import views as shop_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.core.urls')),
    path('api/', include('apps.inventory.urls')),
    path('api/', include('apps.sales.urls')),
    path('api/', include('apps.reports.urls')),
    path('', include('apps.shop.urls')),
    path('login/', shop_views.login_view, name='login'),
]
