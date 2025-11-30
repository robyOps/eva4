from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import Company
from apps.core.validators import validate_rut


class User(AbstractUser):
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_ADMIN_CLIENTE = 'admin_cliente'
    ROLE_GERENTE = 'gerente'
    ROLE_VENDEDOR = 'vendedor'
    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_ADMIN_CLIENTE, 'Admin Cliente'),
        (ROLE_GERENTE, 'Gerente'),
        (ROLE_VENDEDOR, 'Vendedor'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VENDEDOR)
    rut = models.CharField(max_length=20, validators=[validate_rut])
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ['email', 'rut']

    def save(self, *args, **kwargs):
        if self.role == self.ROLE_SUPER_ADMIN:
            self.company = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
