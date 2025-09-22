from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from .models import ProjectLog, TaskLog, TaskUserLog, SystemLog
from .serializers import (
    ProjectLogSerializer, TaskLogSerializer, TaskUserLogSerializer,
    TaskUserLogCreateSerializer, SystemLogSerializer
)


class ProjectLogListView(generics.ListAPIView):
    """项目日志列表视图"""
    serializer_class = ProjectLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        log_type = self.request.query_params.get('log_type')
        user_id = self.request.query_params.get('user_id')

        queryset = ProjectLog.objects.select_related('user', 'project', 'related_user')

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-created_at')


class TaskLogListView(generics.ListAPIView):
    """任务日志列表视图"""
    serializer_class = TaskLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        log_type = self.request.query_params.get('log_type')
        user_id = self.request.query_params.get('user_id')

        queryset = TaskLog.objects.select_related('user', 'task', 'related_user')

        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-created_at')


class TaskUserLogListCreateView(generics.ListCreateAPIView):
    """任务用户日志列表和创建视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskUserLogCreateSerializer
        return TaskUserLogSerializer

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        log_type = self.request.query_params.get('log_type')
        is_private = self.request.query_params.get('is_private')

        queryset = TaskUserLog.objects.select_related('user', 'task').prefetch_related(
            'related_users', 'attachments'
        )

        # 只显示用户有权限查看的日志
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(user=self.request.user) |
                Q(is_private=False) |
                Q(related_users=self.request.user)
            ).distinct()

        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        if is_private is not None:
            queryset = queryset.filter(is_private=is_private.lower() == 'true')

        return queryset.order_by('-logged_at')


class TaskUserLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """任务用户日志详情视图"""
    serializer_class = TaskUserLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = TaskUserLog.objects.select_related('user', 'task').prefetch_related(
            'related_users', 'attachments'
        )

        # 只允许操作用户自己的日志或管理员
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        return queryset


class SystemLogListView(generics.ListAPIView):
    """系统日志列表视图 - 仅管理员可访问"""
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        level = self.request.query_params.get('level')
        log_type = self.request.query_params.get('log_type')
        user_id = self.request.query_params.get('user_id')

        queryset = SystemLog.objects.select_related('user')

        if level:
            queryset = queryset.filter(level=level)
        if log_type:
            queryset = queryset.filter(log_type=log_type)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def log_statistics(request):
    """日志统计信息"""
    # 项目日志统计
    project_logs_count = ProjectLog.objects.count()

    # 任务日志统计
    task_logs_count = TaskLog.objects.count()

    # 用户日志统计
    user_logs_count = TaskUserLog.objects.filter(user=request.user).count()

    # 系统日志统计（仅管理员可见）
    system_logs_count = 0
    if request.user.is_staff:
        system_logs_count = SystemLog.objects.count()

    return Response({
        'project_logs_count': project_logs_count,
        'task_logs_count': task_logs_count,
        'user_logs_count': user_logs_count,
        'system_logs_count': system_logs_count,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recent_logs(request):
    """获取最近的日志"""
    limit = int(request.query_params.get('limit', 10))

    # 获取最近的项目日志
    recent_project_logs = ProjectLog.objects.select_related(
        'user', 'project'
    ).order_by('-created_at')[:limit]

    # 获取最近的任务日志
    recent_task_logs = TaskLog.objects.select_related(
        'user', 'task'
    ).order_by('-created_at')[:limit]

    # 获取用户的最近日志
    recent_user_logs = TaskUserLog.objects.filter(
        user=request.user
    ).select_related('task').order_by('-logged_at')[:limit]

    return Response({
        'project_logs': ProjectLogSerializer(recent_project_logs, many=True).data,
        'task_logs': TaskLogSerializer(recent_task_logs, many=True).data,
        'user_logs': TaskUserLogSerializer(recent_user_logs, many=True).data,
    })