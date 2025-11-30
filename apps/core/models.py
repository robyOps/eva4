from django.db import models
from .validators import validate_rut


class Company(models.Model):
    name = models.CharField(max_length=255)
    rut = models.CharField(max_length=20, unique=True, validators=[validate_rut])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    PLAN_BASICO = 'BASICO'
    PLAN_ESTANDAR = 'ESTANDAR'
    PLAN_PREMIUM = 'PREMIUM'
    PLAN_CHOICES = [
        (PLAN_BASICO, 'Básico'),
        (PLAN_ESTANDAR, 'Estándar'),
        (PLAN_PREMIUM, 'Premium'),
    ]
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='subscription')
    plan_name = models.CharField(max_length=20, choices=PLAN_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company} - {self.plan_name}"

    @property
    def branch_limit(self):
        if self.plan_name == self.PLAN_BASICO:
            return 1
        if self.plan_name == self.PLAN_ESTANDAR:
            return 3
        return None

    @property
    def reports_enabled(self):
        return self.plan_name in {self.PLAN_ESTANDAR, self.PLAN_PREMIUM}
