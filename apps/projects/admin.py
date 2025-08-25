from django.contrib import admin
from .models import (
    Project, ProjectMembership, Task, TaskComment, TaskAttachment, 
    RatingSession, Rating, ProjectLog, Points, PointsHistory, 
    ProjectPoints, PointsEvaluation, EvaluationRecord, MemberRecruitment,
    MemberApplication, ProjectRevenue, RevenueDistribution, TaskTeam, TaskTeamMembership
)

class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ('title', 'assignee', 'status', 'priority', 'due_date', 'progress')
    readonly_fields = ('creator',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'project_type', 'status', 'member_count', 'task_count', 'progress', 'is_active', 'created_at')
    list_filter = ('project_type', 'status', 'is_active', 'created_at', 'owner')
    search_fields = ('name', 'description', 'owner__username', 'tags')
    inlines = [ProjectMembershipInline, TaskInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role', 'contribution_percentage', 'join_date', 'is_active')
    list_filter = ('role', 'is_active', 'join_date', 'project')
    search_fields = ('user__username', 'project__name')

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('author', 'created_at')

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ('uploaded_by', 'file_size', 'uploaded_at')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assignee', 'creator', 'status', 'priority', 'progress', 'due_date', 'is_overdue', 'created_at')
    list_filter = ('status', 'priority', 'project', 'category', 'created_at', 'due_date')
    search_fields = ('title', 'description', 'tags', 'assignee__username', 'creator__username', 'project__name')
    inlines = [TaskCommentInline, TaskAttachmentInline]
    readonly_fields = ('creator', 'completed_at', 'created_at', 'updated_at', 'is_overdue')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 编辑现有对象
            return self.readonly_fields + ('project',)  # 不允许修改所属项目
        return self.readonly_fields

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'content_preview', 'created_at')
    list_filter = ('created_at', 'task__project')
    search_fields = ('content', 'author__username', 'task__title')
    readonly_fields = ('author', 'created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '评论内容'

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'name', 'uploaded_by', 'file_size', 'uploaded_at')
    list_filter = ('uploaded_at', 'task__project')
    search_fields = ('name', 'description', 'uploaded_by__username', 'task__title')
    readonly_fields = ('uploaded_by', 'file_size', 'uploaded_at')

@admin.register(RatingSession)
class RatingSessionAdmin(admin.ModelAdmin):
    list_display = ('project', 'theme', 'created_by', 'status', 'member_count', 'rating_count', 'total_points', 'created_at')
    list_filter = ('status', 'created_at', 'project')
    search_fields = ('theme', 'description', 'project__name', 'created_by__username')
    filter_horizontal = ('selected_members',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('session', 'rater', 'target', 'score', 'created_at')
    list_filter = ('score', 'created_at', 'session__project')
    search_fields = ('rater__username', 'target__username', 'session__theme', 'remark')

@admin.register(ProjectLog)
class ProjectLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'log_type', 'user', 'title', 'created_at')
    list_filter = ('log_type', 'created_at', 'project')
    search_fields = ('title', 'description', 'user__username', 'project__name')
    readonly_fields = ('created_at', 'changes', 'metadata')
    
    def has_add_permission(self, request):
        # 一般情况下不允许手动添加日志，因为日志通过信号自动创建
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        # 只允许超级用户修改日志
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        # 只允许超级用户删除日志
        return request.user.is_superuser

@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'available_points', 'used_points', 'level', 'level_name', 'updated_at')
    list_filter = ('level', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'level_name')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(PointsHistory)
class PointsHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'change_type', 'points', 'reason', 'balance_after', 'related_project', 'created_at')
    list_filter = ('change_type', 'created_at', 'related_project')
    search_fields = ('user__username', 'reason', 'related_project__name')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(ProjectPoints)
class ProjectPointsAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'points', 'contribution_score', 'allocated_by', 'is_final', 'created_at')
    list_filter = ('is_final', 'created_at', 'project')
    search_fields = ('project__name', 'user__username', 'allocated_by__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PointsEvaluation)
class PointsEvaluationAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'created_by', 'status', 'participant_count', 'evaluation_count', 'total_points', 'start_time', 'end_time')
    list_filter = ('status', 'created_at', 'start_time', 'end_time')
    search_fields = ('name', 'description', 'project__name', 'created_by__username')
    filter_horizontal = ('participants',)
    readonly_fields = ('participant_count', 'evaluation_count', 'created_at')

@admin.register(EvaluationRecord)
class EvaluationRecordAdmin(admin.ModelAdmin):
    list_display = ('evaluation', 'evaluator', 'evaluated_user', 'score', 'created_at')
    list_filter = ('score', 'created_at', 'evaluation__project')
    search_fields = ('evaluator__username', 'evaluated_user__username', 'evaluation__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')

# 新增模型的admin配置
@admin.register(MemberRecruitment)
class MemberRecruitmentAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'created_by', 'status', 'positions_needed', 'positions_filled', 'work_type', 'deadline', 'created_at')
    list_filter = ('status', 'work_type', 'skill_level_required', 'created_at', 'deadline', 'project')
    search_fields = ('title', 'description', 'project__name', 'created_by__username', 'required_skills')
    readonly_fields = ('created_by', 'positions_filled', 'is_active', 'application_count', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建时
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

class MemberApplicationInline(admin.TabularInline):
    model = MemberApplication
    extra = 0
    readonly_fields = ('applicant', 'status', 'created_at')
    fields = ('applicant', 'status', 'cover_letter', 'reviewed_by', 'review_notes')

@admin.register(MemberApplication)
class MemberApplicationAdmin(admin.ModelAdmin):
    list_display = ('recruitment', 'applicant', 'status', 'reviewed_by', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'reviewed_at', 'recruitment__project')
    search_fields = ('applicant__username', 'recruitment__title', 'cover_letter', 'skills')
    readonly_fields = ('applicant', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建时
            obj.applicant = request.user
        super().save_model(request, obj, form, change)

class RevenueDistributionInline(admin.TabularInline):
    model = RevenueDistribution
    extra = 0
    readonly_fields = ('member', 'amount', 'equity_percentage_at_time', 'created_at')

@admin.register(ProjectRevenue)
class ProjectRevenueAdmin(admin.ModelAdmin):
    list_display = ('project', 'revenue_type', 'amount', 'net_amount', 'recorded_by', 'is_distributed', 'revenue_date', 'created_at')
    list_filter = ('revenue_type', 'is_distributed', 'revenue_date', 'created_at', 'project')
    search_fields = ('project__name', 'description', 'source', 'recorded_by__username')
    readonly_fields = ('recorded_by', 'net_amount', 'is_distributed', 'distribution_date', 'created_at', 'updated_at')
    inlines = [RevenueDistributionInline]
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建时
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(RevenueDistribution)
class RevenueDistributionAdmin(admin.ModelAdmin):
    list_display = ('revenue', 'member', 'amount', 'equity_percentage_at_time', 'is_paid', 'paid_at', 'created_at')
    list_filter = ('is_paid', 'paid_at', 'created_at', 'revenue__project')
    search_fields = ('member__username', 'revenue__project__name', 'payment_method', 'payment_reference')
    readonly_fields = ('member', 'membership', 'amount', 'equity_percentage_at_time', 'created_at')

class TaskTeamMembershipInline(admin.TabularInline):
    model = TaskTeamMembership
    extra = 1

@admin.register(TaskTeam)
class TaskTeamAdmin(admin.ModelAdmin):
    list_display = ('task', 'team_leader', 'max_members', 'member_count', 'can_add_member', 'created_at')
    list_filter = ('max_members', 'created_at', 'task__project')
    search_fields = ('task__title', 'team_leader__username', 'task__project__name')
    readonly_fields = ('member_count', 'can_add_member', 'created_at')
    inlines = [TaskTeamMembershipInline]

@admin.register(TaskTeamMembership)
class TaskTeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('team', 'user', 'role', 'work_weight', 'peer_evaluation_score', 'self_evaluation_score', 'joined_at')
    list_filter = ('role', 'joined_at', 'team__task__project')
    search_fields = ('user__username', 'team__task__title', 'team__task__project__name')
    readonly_fields = ('joined_at',)