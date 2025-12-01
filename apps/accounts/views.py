from django.contrib.auth import get_user_model
from rest_framework import authentication, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.permissions import IsActive
from .permissions import IsAdminOrSuper
from .serializers import UserSerializer, MeSerializer

User = get_user_model()


class UserCreateView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsActive, IsAdminOrSuper]

    def get_queryset(self):
        return User.objects.all()


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActive]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)


class SessionTokenView(APIView):
    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsActive]

    def post(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response({'refresh': str(refresh), 'access': str(refresh.access_token)})
