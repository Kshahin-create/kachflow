from rest_framework import serializers
from apps.accounts.models import ProjectMember, ProjectInvitation
from apps.projects.models import Company, Project, ProjectSetting


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("owner",)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class ProjectSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSetting
        fields = "__all__"


class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ProjectMember
        fields = "__all__"


class ProjectInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvitation
        fields = "__all__"
        read_only_fields = ("token", "invited_by", "accepted_at", "created_at")
