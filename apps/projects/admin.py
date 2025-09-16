from django.contrib import admin
from .models import (
    Project, ProjectMembership, ProjectLog,
    MemberRecruitment, MemberApplication, ProjectRevenue, RevenueDistribution
)

class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'project_type', 'status', 'member_count', 'progress', 'is_active', 'created_at')
    list_filter = ('project_type', 'status', 'is_active', 'created_at', 'owner')
    search_fields = ('name', 'description', 'owner__username', 'tags')
    inlines = [ProjectMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role', 'contribution_percentage', 'join_date', 'is_active')
    list_filter = ('role', 'is_active', 'join_date', 'project')
    search_fields = ('user__username', 'project__name')

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