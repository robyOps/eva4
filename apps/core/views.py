from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Company, Subscription
from .serializers import CompanySerializer, SubscriptionSerializer
from .permissions import IsSuperAdmin


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated & IsSuperAdmin]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated & IsSuperAdmin])
    def subscribe(self, request, pk=None):
        company = self.get_object()
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub, _ = Subscription.objects.update_or_create(
            company=company,
            defaults=serializer.validated_data,
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)
