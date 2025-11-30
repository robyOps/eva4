from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.core.models import Company
from apps.core.validators import validate_rut
from apps.core.serializers import CompanySerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False, allow_null=True)
    rut = serializers.CharField(validators=[validate_rut])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'rut', 'company', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate(self, attrs):
        request = self.context['request']
        acting_user: User = request.user
        role = attrs.get('role', User.ROLE_VENDEDOR)
        company = attrs.get('company')
        if acting_user.role == User.ROLE_SUPER_ADMIN:
            if role != User.ROLE_ADMIN_CLIENTE:
                raise serializers.ValidationError('Super admin solo crea admin_cliente')
            if not company:
                raise serializers.ValidationError('Debe indicar company para admin_cliente')
        elif acting_user.role == User.ROLE_ADMIN_CLIENTE:
            if role not in [User.ROLE_GERENTE, User.ROLE_VENDEDOR]:
                raise serializers.ValidationError('Admin cliente solo crea gerente o vendedor')
            attrs['company'] = acting_user.company
        else:
            raise serializers.ValidationError('Sin permisos')
        return attrs


class MeSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'rut', 'company', 'is_active']
