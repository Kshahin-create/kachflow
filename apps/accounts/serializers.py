from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.accounts.models import UserProfile, ProjectMember, ProjectInvitation, ProjectStakeholder

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_active")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"


class ProjectMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMember
        fields = "__all__"


class ProjectInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvitation
        fields = "__all__"


class ProjectStakeholderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStakeholder
        fields = "__all__"
