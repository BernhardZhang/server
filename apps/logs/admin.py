from django.contrib import admin
from .models import ProjectLog, TaskLog, TaskUserLog, TaskUserLogAttachment, SystemLog


@admin.register(ProjectLog)
class ProjectLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'log_type', 'user', 'title', 'created_at')
    list_filter = ('log_type', 'created_at', 'project')
    search_fields = ('title', 'description', 'user__username', 'project__name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('project', 'user', 'related_user')

    fieldsets = (
        ('基本信息', {
            'fields': ('project', 'log_type', 'user', 'title', 'description')
        }),
        ('操作详情', {
            'fields': ('action_method', 'action_function', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('关联信息', {
            'fields': ('related_user', 'changes', 'metadata'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'log_type', 'user', 'title', 'created_at')
    list_filter = ('log_type', 'created_at')
    search_fields = ('title', 'description', 'user__username', 'task__title')
    readonly_fields = ('created_at',)
    raw_id_fields = ('task', 'user', 'related_user')

    fieldsets = (
        ('基本信息', {
            'fields': ('task', 'log_type', 'user', 'title', 'description')
        }),
        ('操作详情', {
            'fields': ('action_method', 'action_function', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('关联信息', {
            'fields': ('related_user', 'changes', 'metadata'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class TaskUserLogAttachmentInline(admin.TabularInline):
    model = TaskUserLogAttachment
    extra = 0
    readonly_fields = ('file_size', 'uploaded_at')


@admin.register(TaskUserLog)
class TaskUserLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'log_type', 'title', 'progress_percentage', 'logged_at')
    list_filter = ('log_type', 'priority', 'is_important', 'is_private', 'logged_at')
    search_fields = ('title', 'content', 'user__username', 'task__title')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('task', 'user')
    filter_horizontal = ('related_users',)
    inlines = [TaskUserLogAttachmentInline]

    fieldsets = (
        ('基本信息', {
            'fields': ('task', 'user', 'log_type', 'title', 'content')
        }),
        ('工作信息', {
            'fields': ('work_duration', 'progress_percentage', 'location')
        }),
        ('分类标记', {
            'fields': ('tags', 'priority', 'is_important', 'is_private')
        }),
        ('关联信息', {
            'fields': ('related_users',)
        }),
        ('时间信息', {
            'fields': ('logged_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'log_type', 'title', 'user', 'created_at')
    list_filter = ('level', 'log_type', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)

    fieldsets = (
        ('基本信息', {
            'fields': ('level', 'log_type', 'title', 'message', 'user')
        }),
        ('请求信息', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method'),
            'classes': ('collapse',)
        }),
        ('额外数据', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )