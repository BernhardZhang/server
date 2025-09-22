from rest_framework import serializers
from .models import ProjectLog, TaskLog, TaskUserLog, TaskUserLogAttachment, SystemLog


class ProjectLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    related_user_name = serializers.CharField(source='related_user.username', read_only=True)

    class Meta:
        model = ProjectLog
        fields = [
            'id', 'project', 'project_name', 'log_type', 'log_type_display',
            'user', 'user_name', 'title', 'description', 'action_method',
            'action_function', 'related_user', 'related_user_name',
            'changes', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']


class TaskLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    related_user_name = serializers.CharField(source='related_user.username', read_only=True)

    class Meta:
        model = TaskLog
        fields = [
            'id', 'task', 'task_title', 'log_type', 'log_type_display',
            'user', 'user_name', 'title', 'description', 'action_method',
            'action_function', 'related_user', 'related_user_name',
            'changes', 'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']


class TaskUserLogAttachmentSerializer(serializers.ModelSerializer):
    file_size_display = serializers.CharField(read_only=True)

    class Meta:
        model = TaskUserLogAttachment
        fields = [
            'id', 'file', 'filename', 'file_type', 'file_size',
            'file_size_display', 'description', 'uploaded_at'
        ]
        read_only_fields = ['file_size', 'uploaded_at']


class TaskUserLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    attachments = TaskUserLogAttachmentSerializer(many=True, read_only=True)
    related_users_names = serializers.StringRelatedField(source='related_users', many=True, read_only=True)

    class Meta:
        model = TaskUserLog
        fields = [
            'id', 'task', 'task_title', 'user', 'user_name', 'log_type',
            'log_type_display', 'title', 'content', 'work_duration',
            'progress_percentage', 'location', 'tags', 'priority',
            'related_users', 'related_users_names', 'is_important',
            'is_private', 'attachments', 'logged_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class TaskUserLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskUserLog
        fields = [
            'task', 'log_type', 'title', 'content', 'work_duration',
            'progress_percentage', 'location', 'tags', 'priority',
            'related_users', 'is_important', 'is_private', 'logged_at'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SystemLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)

    class Meta:
        model = SystemLog
        fields = [
            'id', 'level', 'level_display', 'log_type', 'log_type_display',
            'title', 'message', 'user', 'user_name', 'ip_address',
            'user_agent', 'request_path', 'request_method', 'extra_data',
            'created_at'
        ]
        read_only_fields = ['created_at']