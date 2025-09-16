from rest_framework import serializers
from .models import (
    Project, ProjectMembership, ProjectLog,
    MemberRecruitment, MemberApplication, ProjectRevenue, RevenueDistribution
)
from django.contrib.auth import get_user_model
User = get_user_model()

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ('user', 'user_name', 'contribution_percentage', 'join_date')

class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    members_detail = ProjectMembershipSerializer(source='projectmembership_set', many=True, read_only=True)
    member_count = serializers.ReadOnlyField()
    tag_list = serializers.ReadOnlyField()
    recent_logs = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'owner', 'owner_name', 'members_detail',
            'member_count', 'project_type', 'status', 'tags', 'tag_list', 'progress',
            'total_investment', 'valuation',
            'is_active', 'is_public', 'start_date', 'end_date', 'created_at', 'updated_at',
            'recent_logs'
        )

    def get_recent_logs(self, obj):
        """获取最近的项目日志"""
        logs = obj.logs.all()[:5]
        return ProjectLogSerializer(logs, many=True).data

class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'name', 'description', 'project_type', 'tags', 'progress',
            'total_investment', 'valuation', 'is_public', 'start_date', 'end_date'
        )

    def create(self, validated_data):
        # 自动将当前用户设置为项目负责人
        validated_data['owner'] = self.context['request'].user
        project = super().create(validated_data)

        # 自动将创建者添加为项目成员（角色为owner）
        ProjectMembership.objects.create(
            user=project.owner,
            project=project,
            role='owner'
        )

        return project

class ProjectLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    related_user_name = serializers.CharField(source='related_user.username', read_only=True)

    class Meta:
        model = ProjectLog
        fields = (
            'id', 'log_type', 'user', 'user_name', 'title', 'description',
            'related_user', 'related_user_name', 'changes', 'metadata', 'created_at'
        )

# 招募相关序列化器
class MemberRecruitmentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    is_active = serializers.ReadOnlyField()
    application_count = serializers.ReadOnlyField()

    class Meta:
        model = MemberRecruitment
        fields = (
            'id', 'project', 'project_name', 'title', 'description', 'required_skills',
            'skill_level_required', 'positions_needed', 'positions_filled', 'work_type',
            'expected_commitment', 'salary_range', 'equity_percentage_min', 'equity_percentage_max',
            'status', 'deadline', 'created_by', 'created_by_name', 'is_active', 'application_count',
            'created_at', 'updated_at'
        )

class MemberRecruitmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberRecruitment
        fields = (
            'project', 'title', 'description', 'required_skills', 'skill_level_required',
            'positions_needed', 'work_type', 'expected_commitment', 'salary_range',
            'equity_percentage_min', 'equity_percentage_max', 'deadline'
        )

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class MemberApplicationSerializer(serializers.ModelSerializer):
    recruitment_title = serializers.CharField(source='recruitment.title', read_only=True)
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = MemberApplication
        fields = (
            'id', 'recruitment', 'recruitment_title', 'applicant', 'applicant_name',
            'cover_letter', 'skills', 'experience', 'portfolio_url', 'expected_commitment',
            'status', 'reviewed_by', 'reviewed_by_name', 'review_notes', 'reviewed_at',
            'created_at', 'updated_at'
        )

class MemberApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberApplication
        fields = (
            'recruitment', 'cover_letter', 'skills', 'experience',
            'portfolio_url', 'expected_commitment'
        )

    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user
        return super().create(validated_data)

# 收益相关序列化器
class ProjectRevenueSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.username', read_only=True)

    class Meta:
        model = ProjectRevenue
        fields = (
            'id', 'project', 'project_name', 'revenue_type', 'amount', 'description',
            'source', 'associated_costs', 'net_amount', 'revenue_date', 'recorded_by',
            'recorded_by_name', 'is_distributed', 'distribution_date', 'created_at', 'updated_at'
        )

class ProjectRevenueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRevenue
        fields = (
            'project', 'revenue_type', 'amount', 'description', 'source',
            'associated_costs', 'revenue_date'
        )

    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)

class RevenueDistributionSerializer(serializers.ModelSerializer):
    revenue_description = serializers.CharField(source='revenue.description', read_only=True)
    member_name = serializers.CharField(source='member.username', read_only=True)

    class Meta:
        model = RevenueDistribution
        fields = (
            'id', 'revenue', 'revenue_description', 'member', 'member_name',
            'amount', 'equity_percentage_at_time', 'is_paid', 'paid_at',
            'payment_method', 'payment_reference', 'created_at'
        )