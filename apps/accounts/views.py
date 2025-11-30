from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.permissions import IsActive
from .serializers import UserSerializer, MeSerializer

User = get_user_model()


class UserCreateView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsActive]

    def get_queryset(self):
        return User.objects.all()


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActive]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)
