from django.contrib.auth import get_user_model
from rest_framework import viewsets
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(project_memberships__project__members__user=self.request.user).distinct()
