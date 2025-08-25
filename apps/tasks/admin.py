from django.contrib import admin
from .models import Task, TaskComment, TaskAttachment, TaskEvaluation, TaskEvaluationSession, TaskLog

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'assignee', 'status', 'priority', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'created_at', 'due_date']
    search_fields = ['title', 'description', 'creator__username', 'assignee__username']

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['task__title', 'author__username', 'content']

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'filename', 'file_type', 'file_size_display', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at', 'file_type']
    search_fields = ['task__title', 'filename', 'uploaded_by__username']
    readonly_fields = ['file_size', 'file_size_display']

@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'description', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['task__title', 'user__username', 'description']
    readonly_fields = ['task', 'user', 'action', 'description', 'old_value', 'new_value', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        # 不允许手动添加日志记录
        return False
    
    def has_change_permission(self, request, obj=None):
        # 不允许修改日志记录
        return False

@admin.register(TaskEvaluation)
class TaskEvaluationAdmin(admin.ModelAdmin):
    list_display = ['task', 'evaluator', 'evaluated_user', 'total_score', 'created_at']
    list_filter = ['score_type', 'evaluation_mode', 'created_at']
    search_fields = ['task__title', 'evaluator__username', 'evaluated_user__username']

@admin.register(TaskEvaluationSession)
class TaskEvaluationSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'created_by', 'status', 'completion_percentage', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'project__name', 'created_by__username']
    readonly_fields = ['completion_percentage']