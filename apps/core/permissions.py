from rest_framework.permissions import BasePermission
from apps.core.models import Subscription


class IsActive(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == request.user.ROLE_SUPER_ADMIN)


class CompanyPlanAllowsReports(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.company:
            return False
        subscription = getattr(user.company, 'subscription', None)
        return bool(subscription and subscription.reports_enabled and subscription.active)
