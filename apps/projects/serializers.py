from rest_framework import serializers
from .models import (
    Project, ProjectMembership, Task, TaskComment, TaskAttachment, ProjectLog,
    Points, PointsHistory, ProjectPoints, PointsEvaluation, EvaluationRecord,
    TaskAssignment, WislabMembership, ProjectDataAnalysis, MemberRecruitment,
    MemberApplication, ProjectRevenue, RevenueDistribution, TaskTeam, TaskTeamMembership,
    RatingSession, Rating
)
from django.contrib.auth import get_user_model
User = get_user_model()

class SimpleTaskSerializer(serializers.ModelSerializer):
    """简化的任务序列化器，用于项目详情中显示任务列表"""
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = (
            'id', 'title', 'status', 'priority', 'assignee', 'assignee_name',
            'due_date', 'progress', 'created_at', 'is_overdue'
        )

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ProjectMembership
        fields = ('user', 'user_name', 'contribution_percentage', 'join_date')

class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    members_detail = ProjectMembershipSerializer(source='projectmembership_set', many=True, read_only=True)
    member_count = serializers.ReadOnlyField()
    tasks = SimpleTaskSerializer(many=True, read_only=True)
    tag_list = serializers.ReadOnlyField()
    recent_logs = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'owner', 'owner_name', 'members_detail', 
            'member_count', 'project_type', 'status', 'tags', 'tag_list', 'progress', 
            'task_count', 'completed_tasks', 'total_investment', 'valuation', 
            'is_active', 'is_public', 'start_date', 'end_date', 'created_at', 'updated_at', 
            'tasks', 'recent_logs'
        )
    
    def get_recent_logs(self, obj):
        """获取最近的项目日志"""
        recent_logs = obj.logs.all()[:10]  # 获取最近10条日志
        return ProjectLogSerializer(recent_logs, many=True).data

class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('name', 'description', 'project_type', 'status', 'tags', 'is_public', 'progress', 'start_date', 'end_date')

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        project = super().create(validated_data)
        # 自动将项目创建者添加为项目成员
        from .models import ProjectMembership
        ProjectMembership.objects.get_or_create(
            user=project.owner,
            project=project,
            defaults={'contribution_percentage': 0.00}
        )
        return project

    def to_representation(self, instance):
        # 刷新实例以确保相关数据被正确加载
        instance.refresh_from_db()
        # 使用完整的ProjectSerializer来返回创建后的项目数据
        return ProjectSerializer(instance, context=self.context).data

class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = ('id', 'content', 'author', 'author_name', 'created_at', 'updated_at')
        read_only_fields = ('author',)

class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = ('id', 'file', 'name', 'description', 'file_size', 'uploaded_by', 'uploaded_by_name', 'uploaded_at')
        read_only_fields = ('uploaded_by', 'file_size')

class TaskSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    tag_list = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'project_name', 
            'assignee', 'assignee_name', 'creator', 'creator_name',
            'status', 'priority', 'start_date', 'due_date', 'completed_at',
            'progress', 'estimated_hours', 'actual_hours', 'tags', 'tag_list',
            'category', 'created_at', 'updated_at', 'comments', 'attachments',
            'is_overdue'
        )
        read_only_fields = ('creator', 'completed_at')

class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'title', 'description', 'project', 'assignee', 'status', 
            'priority', 'start_date', 'due_date', 'progress', 
            'estimated_hours', 'tags', 'category'
        )
    
    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return TaskSerializer(instance, context=self.context).data

class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'title', 'description', 'assignee', 'status', 'priority', 
            'start_date', 'due_date', 'progress', 'estimated_hours', 
            'actual_hours', 'tags', 'category'
        )
    
    def to_representation(self, instance):
        return TaskSerializer(instance, context=self.context).data

class ProjectLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar', read_only=True)
    related_task_title = serializers.CharField(source='related_task.title', read_only=True)
    related_user_name = serializers.CharField(source='related_user.username', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    
    class Meta:
        model = ProjectLog
        fields = (
            'id', 'log_type', 'log_type_display', 'user', 'user_name', 'user_avatar',
            'title', 'description', 'related_task', 'related_task_title', 
            'related_user', 'related_user_name', 'changes', 'metadata', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

class PointsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    level_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Points
        fields = (
            'id', 'user', 'user_name', 'total_points', 'available_points', 
            'used_points', 'level', 'level_name', 'created_at', 'updated_at'
        )
        read_only_fields = ('user', 'level', 'created_at', 'updated_at')

class PointsHistorySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    change_type_display = serializers.CharField(source='get_change_type_display', read_only=True)
    related_project_name = serializers.CharField(source='related_project.name', read_only=True)
    related_task_title = serializers.CharField(source='related_task.title', read_only=True)
    related_user_name = serializers.CharField(source='related_user.username', read_only=True)
    
    class Meta:
        model = PointsHistory
        fields = (
            'id', 'user', 'user_name', 'change_type', 'change_type_display',
            'points', 'reason', 'balance_after', 'related_project', 
            'related_project_name', 'related_task', 'related_task_title',
            'related_user', 'related_user_name', 'created_at'
        )
        read_only_fields = ('user', 'balance_after', 'created_at')

class ProjectPointsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    allocated_by_name = serializers.CharField(source='allocated_by.username', read_only=True)
    
    class Meta:
        model = ProjectPoints
        fields = (
            'id', 'project', 'project_name', 'user', 'user_name', 
            'points', 'contribution_score', 'allocation_reason',
            'allocated_by', 'allocated_by_name', 'is_final',
            'created_at', 'updated_at'
        )
        read_only_fields = ('allocated_by', 'created_at', 'updated_at')

class EvaluationRecordSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source='evaluator.username', read_only=True)
    evaluated_user_name = serializers.CharField(source='evaluated_user.username', read_only=True)
    
    class Meta:
        model = EvaluationRecord
        fields = (
            'id', 'evaluation', 'evaluator', 'evaluator_name',
            'evaluated_user', 'evaluated_user_name', 'score', 'comment',
            'criteria_scores', 'created_at', 'updated_at'
        )
        read_only_fields = ('evaluator', 'created_at', 'updated_at')

class PointsEvaluationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    participant_count = serializers.ReadOnlyField()
    evaluation_count = serializers.ReadOnlyField()
    evaluation_records = EvaluationRecordSerializer(many=True, read_only=True)
    participants_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PointsEvaluation
        fields = (
            'id', 'project', 'project_name', 'name', 'description', 
            'total_points', 'created_by', 'created_by_name',
            'participants', 'participants_detail', 'participant_count',
            'status', 'start_time', 'end_time', 'evaluation_count',
            'evaluation_records', 'created_at'
        )
        read_only_fields = ('created_by', 'evaluation_count', 'created_at')
    
    def get_participants_detail(self, obj):
        participants = obj.participants.all()
        return [{'id': user.id, 'username': user.username} for user in participants]

class PointsEvaluationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsEvaluation
        fields = (
            'project', 'name', 'description', 'total_points',
            'participants', 'start_time', 'end_time'
        )
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return PointsEvaluationSerializer(instance, context=self.context).data

class TaskAssignmentSerializer(serializers.ModelSerializer):
    """任务分配序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskAssignment
        fields = (
            'id', 'task', 'task_title', 'user', 'user_name', 
            'role_weight', 'system_score', 'function_score', 
            'total_score', 'assigned_at'
        )
        read_only_fields = ('system_score', 'function_score', 'total_score', 'assigned_at')

class WislabMembershipSerializer(serializers.ModelSerializer):
    """WISlab会员序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    membership_type_display = serializers.CharField(source='get_membership_type_display', read_only=True)
    current_project_count = serializers.ReadOnlyField()
    can_join_project_status = serializers.SerializerMethodField()
    is_membership_valid_status = serializers.SerializerMethodField()
    
    class Meta:
        model = WislabMembership
        fields = (
            'id', 'user', 'user_name', 'membership_type', 'membership_type_display',
            'project_limit', 'expire_date', 'total_points', 'available_points',
            'is_active', 'current_project_count', 'can_join_project_status',
            'is_membership_valid_status', 'created_at', 'updated_at'
        )
        read_only_fields = ('user', 'current_project_count', 'created_at', 'updated_at')
    
    def get_can_join_project_status(self, obj):
        return obj.can_join_project()
    
    def get_is_membership_valid_status(self, obj):
        return obj.is_membership_valid()

class ProjectDataAnalysisSerializer(serializers.ModelSerializer):
    """项目数据分析序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = ProjectDataAnalysis
        fields = (
            'id', 'project', 'project_name', 'total_system_score',
            'total_function_score', 'total_score', 'avg_system_score',
            'avg_function_score', 'member_scores', 'analysis_summary',
            'last_updated'
        )
        read_only_fields = ('project', 'last_updated')

class WislabTaskSerializer(TaskSerializer):
    """扩展的任务序列化器，包含WISlab功能"""
    assignments = TaskAssignmentSerializer(source='taskassignment_set', many=True, read_only=True)
    system_score = serializers.ReadOnlyField()
    function_score = serializers.ReadOnlyField()
    time_coefficient = serializers.ReadOnlyField()
    assignees_detail = serializers.SerializerMethodField()
    
    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + (
            'role_weights', 'assignees', 'assignments', 'system_score',
            'function_score', 'time_coefficient', 'assignees_detail'
        )
    
    def get_assignees_detail(self, obj):
        """获取任务负责人详情"""
        assignments = obj.taskassignment_set.all()
        return [{
            'user_id': assignment.user.id,
            'username': assignment.user.username,
            'role_weight': float(assignment.role_weight),
            'system_score': float(assignment.system_score),
            'function_score': float(assignment.function_score),
            'total_score': float(assignment.total_score)
        } for assignment in assignments]

class WislabProjectSerializer(ProjectSerializer):
    """扩展的项目序列化器，包含WISlab功能"""
    data_analysis = ProjectDataAnalysisSerializer(read_only=True)
    evaluations = PointsEvaluationSerializer(many=True, read_only=True)
    tasks = WislabTaskSerializer(many=True, read_only=True)
    
    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ('data_analysis', 'evaluations')

class WislabProjectCreateSerializer(ProjectCreateSerializer):
    """WISlab项目创建序列化器，包含会员权限检查"""
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # 检查用户会员权限
        try:
            membership = user.wislab_membership
            if not membership.can_join_project():
                raise serializers.ValidationError(
                    f"普通会员最多只能参与{membership.project_limit}个项目，"
                    f"当前已参与{membership.current_project_count}个项目。"
                    "请升级为VIP会员以解除项目限制。"
                )
        except WislabMembership.DoesNotExist:
            # 如果没有会员记录，创建一个默认的普通会员记录
            WislabMembership.objects.create(user=user)
            # 检查项目数量限制
            current_count = user.projects.filter(status='active').count()
            if current_count >= 5:
                raise serializers.ValidationError(
                    "普通会员最多只能参与5个项目。请升级为VIP会员以解除项目限制。"
                )
        
        return attrs
    
    def create(self, validated_data):
        project = super().create(validated_data)
        
        # 创建项目数据分析记录
        ProjectDataAnalysis.objects.create(project=project)
        
        return project
    
    def to_representation(self, instance):
        return WislabProjectSerializer(instance, context=self.context).data

class MemberRecruitmentSerializer(serializers.ModelSerializer):
    """成员招募序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    skill_level_required_display = serializers.CharField(source='get_skill_level_required_display', read_only=True)
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.ReadOnlyField()
    application_count = serializers.ReadOnlyField()
    
    class Meta:
        model = MemberRecruitment
        fields = (
            'id', 'project', 'project_name', 'title', 'description', 'required_skills',
            'skill_level_required', 'skill_level_required_display', 'positions_needed',
            'positions_filled', 'work_type', 'work_type_display', 'expected_commitment',
            'salary_range', 'equity_percentage_min', 'equity_percentage_max', 
            'status', 'status_display', 'deadline', 'created_by', 'created_by_name',
            'is_active', 'application_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_by', 'positions_filled', 'created_at', 'updated_at')

class MemberRecruitmentCreateSerializer(serializers.ModelSerializer):
    """成员招募创建序列化器"""
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
    
    def to_representation(self, instance):
        return MemberRecruitmentSerializer(instance, context=self.context).data

class MemberApplicationSerializer(serializers.ModelSerializer):
    """成员申请序列化器"""
    recruitment_title = serializers.CharField(source='recruitment.title', read_only=True)
    project_name = serializers.CharField(source='recruitment.project.name', read_only=True)
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MemberApplication
        fields = (
            'id', 'recruitment', 'recruitment_title', 'project_name', 'applicant',
            'applicant_name', 'cover_letter', 'skills', 'experience', 'portfolio_url',
            'expected_commitment', 'status', 'status_display', 'reviewed_by',
            'reviewed_by_name', 'review_notes', 'reviewed_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('applicant', 'status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at')

class MemberApplicationCreateSerializer(serializers.ModelSerializer):
    """成员申请创建序列化器"""
    class Meta:
        model = MemberApplication
        fields = (
            'recruitment', 'cover_letter', 'skills', 'experience', 
            'portfolio_url', 'expected_commitment'
        )
    
    def create(self, validated_data):
        validated_data['applicant'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return MemberApplicationSerializer(instance, context=self.context).data

class ProjectRevenueSerializer(serializers.ModelSerializer):
    """项目收益序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.username', read_only=True)
    revenue_type_display = serializers.CharField(source='get_revenue_type_display', read_only=True)
    
    class Meta:
        model = ProjectRevenue
        fields = (
            'id', 'project', 'project_name', 'revenue_type', 'revenue_type_display',
            'amount', 'description', 'source', 'associated_costs', 'net_amount',
            'revenue_date', 'recorded_by', 'recorded_by_name', 'is_distributed',
            'distribution_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('recorded_by', 'net_amount', 'is_distributed', 'distribution_date', 'created_at', 'updated_at')

class ProjectRevenueCreateSerializer(serializers.ModelSerializer):
    """项目收益创建序列化器"""
    class Meta:
        model = ProjectRevenue
        fields = (
            'project', 'revenue_type', 'amount', 'description', 
            'source', 'associated_costs', 'revenue_date'
        )
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return ProjectRevenueSerializer(instance, context=self.context).data

class RevenueDistributionSerializer(serializers.ModelSerializer):
    """收益分配序列化器"""
    member_name = serializers.CharField(source='member.username', read_only=True)
    project_name = serializers.CharField(source='revenue.project.name', read_only=True)
    revenue_amount = serializers.DecimalField(source='revenue.amount', max_digits=12, decimal_places=2, read_only=True)
    revenue_type = serializers.CharField(source='revenue.get_revenue_type_display', read_only=True)
    
    class Meta:
        model = RevenueDistribution
        fields = (
            'id', 'revenue', 'member', 'member_name', 'project_name', 'membership',
            'amount', 'equity_percentage_at_time', 'revenue_amount', 'revenue_type',
            'is_paid', 'paid_at', 'payment_method', 'payment_reference', 'created_at'
        )
        read_only_fields = ('member', 'membership', 'amount', 'equity_percentage_at_time', 'created_at')

class TaskTeamMembershipSerializer(serializers.ModelSerializer):
    """任务团队成员序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = TaskTeamMembership
        fields = (
            'id', 'team', 'user', 'user_name', 'role', 'role_display', 
            'work_weight', 'peer_evaluation_score', 'self_evaluation_score', 'joined_at'
        )
        read_only_fields = ('joined_at',)

class TaskTeamSerializer(serializers.ModelSerializer):
    """任务团队序列化器"""
    task_title = serializers.CharField(source='task.title', read_only=True)
    team_leader_name = serializers.CharField(source='team_leader.username', read_only=True)
    member_count = serializers.ReadOnlyField()
    can_add_member = serializers.ReadOnlyField()
    memberships = TaskTeamMembershipSerializer(source='taskteammembership_set', many=True, read_only=True)
    
    class Meta:
        model = TaskTeam
        fields = (
            'id', 'task', 'task_title', 'team_leader', 'team_leader_name',
            'max_members', 'member_count', 'can_add_member', 'memberships', 'created_at'
        )
        read_only_fields = ('member_count', 'can_add_member', 'created_at')

class TaskTeamCreateSerializer(serializers.ModelSerializer):
    """任务团队创建序列化器"""
    members = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="成员ID列表"
    )
    
    class Meta:
        model = TaskTeam
        fields = ('task', 'team_leader', 'max_members', 'members')
    
    def create(self, validated_data):
        members_ids = validated_data.pop('members', [])
        team = super().create(validated_data)
        
        # 添加团队成员
        for member_id in members_ids:
            try:
                user = User.objects.get(id=member_id)
                role = 'leader' if user.id == team.team_leader.id else 'member'
                TaskTeamMembership.objects.create(
                    team=team,
                    user=user,
                    role=role
                )
            except User.DoesNotExist:
                continue
        
        return team
    
    def to_representation(self, instance):
        return TaskTeamSerializer(instance, context=self.context).data

# 评分功能序列化器
class RatingSessionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    member_count = serializers.ReadOnlyField()
    rating_count = serializers.ReadOnlyField()
    ratings = serializers.SerializerMethodField()
    
    class Meta:
        model = RatingSession
        fields = (
            'id', 'project', 'project_name', 'theme', 'description', 
            'created_by', 'created_by_name', 'status', 'selected_members',
            'total_points', 'member_count', 'rating_count', 'ratings',
            'created_at', 'ended_at'
        )
        read_only_fields = ('created_by', 'created_at', 'ended_at')
    
    def get_ratings(self, obj):
        ratings = obj.ratings.all()
        return RatingSerializer(ratings, many=True).data

class RatingSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingSession
        fields = (
            'project', 'theme', 'description', 'selected_members', 
            'total_points'
        )
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return RatingSessionSerializer(instance, context=self.context).data

class RatingSerializer(serializers.ModelSerializer):
    rater_name = serializers.CharField(source='rater.username', read_only=True)
    target_name = serializers.CharField(source='target.username', read_only=True)
    session_theme = serializers.CharField(source='session.theme', read_only=True)
    
    class Meta:
        model = Rating
        fields = (
            'id', 'session', 'session_theme', 'rater', 'rater_name',
            'target', 'target_name', 'score', 'remark',
            'created_at', 'updated_at'
        )
        read_only_fields = ('rater', 'created_at', 'updated_at')

class RatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ('session', 'target', 'score', 'remark')
    
    def create(self, validated_data):
        validated_data['rater'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        return RatingSerializer(instance, context=self.context).data