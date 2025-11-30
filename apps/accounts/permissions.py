from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model

User = get_user_model()


class RolePermission(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles and user.is_active)


class IsAdminOrGerente(RolePermission):
    allowed_roles = [User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE]


class IsInternal(RolePermission):
    allowed_roles = [User.ROLE_ADMIN_CLIENTE, User.ROLE_GERENTE, User.ROLE_VENDEDOR]
