from rest_framework import serializers
from .models import Company, Subscription
from .validators import validate_rut


class CompanySerializer(serializers.ModelSerializer):
    rut = serializers.CharField(validators=[validate_rut])

    class Meta:
        model = Company
        fields = ['id', 'name', 'rut', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['id', 'company', 'plan_name', 'start_date', 'end_date', 'active']
        read_only_fields = ['id', 'company']

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError('Fecha fin debe ser posterior a inicio')
        return attrs
