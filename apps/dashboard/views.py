from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import DashboardWidget, UserPreference
from .serializers import DashboardWidgetSerializer, DashboardWidgetCreateSerializer, UserPreferenceSerializer

class DashboardWidgetListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DashboardWidgetCreateSerializer
        return DashboardWidgetSerializer

    def get_queryset(self):
        return DashboardWidget.objects.filter(user=self.request.user, is_active=True).order_by('position_y', 'position_x')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DashboardWidgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DashboardWidgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DashboardWidget.objects.filter(user=self.request.user)

class UserPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, created = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

@api_view(['GET'])
def dashboard_overview(request):
    """获取仪表板概览数据"""
    user = request.user
    
    # 基础统计
    from apps.tasks.models import Task
    from apps.projects.models import Project
    from apps.voting.models import Vote
    
    # 我的任务统计
    my_tasks = Task.objects.filter(Q(creator=user) | Q(assignee=user)).distinct()
    task_stats = {
        'total': my_tasks.count(),
        'pending': my_tasks.filter(status='pending').count(),
        'in_progress': my_tasks.filter(status='in_progress').count(),
        'completed': my_tasks.filter(status='completed').count(),
    }
    
    # 我的项目统计
    my_projects = Project.objects.filter(Q(creator=user) | Q(members=user)).distinct()
    project_stats = {
        'total': my_projects.count(),
        'active': my_projects.filter(status='active').count(),
        'completed': my_projects.filter(status='completed').count(),
    }
    
    # 投票统计
    votes_cast = Vote.objects.filter(user=user).count()
    votes_received = Vote.objects.filter(Q(target_user=user) | Q(target_project__members=user)).distinct().count()
    
    # 最近活动
    recent_tasks = Task.objects.filter(
        Q(creator=user) | Q(assignee=user)
    ).distinct().order_by('-updated_at')[:5]
    
    recent_projects = Project.objects.filter(
        Q(creator=user) | Q(members=user)
    ).distinct().order_by('-updated_at')[:5]
    
    return Response({
        'task_stats': task_stats,
        'project_stats': project_stats,
        'voting_stats': {
            'votes_cast': votes_cast,
            'votes_received': votes_received
        },
        'recent_activities': {
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'updated_at': task.updated_at
                } for task in recent_tasks
            ],
            'projects': [
                {
                    'id': project.id,
                    'name': project.name,
                    'status': project.status,
                    'updated_at': project.updated_at
                } for project in recent_projects
            ]
        },
        'user_balance': float(user.balance) if hasattr(user, 'balance') else 0,
        'total_received': float(user.total_received) if hasattr(user, 'total_received') else 0
    })

@api_view(['POST'])
def update_widget_layout(request):
    """批量更新组件布局"""
    widgets_data = request.data.get('widgets', [])
    
    for widget_data in widgets_data:
        widget_id = widget_data.get('id')
        try:
            widget = DashboardWidget.objects.get(id=widget_id, user=request.user)
            widget.position_x = widget_data.get('position_x', widget.position_x)
            widget.position_y = widget_data.get('position_y', widget.position_y)
            widget.width = widget_data.get('width', widget.width)
            widget.height = widget_data.get('height', widget.height)
            widget.save()
        except DashboardWidget.DoesNotExist:
            continue
    
    return Response({'message': '布局更新成功'})

@api_view(['GET'])
def widget_data(request, widget_id):
    """获取特定组件的数据"""
    try:
        widget = DashboardWidget.objects.get(id=widget_id, user=request.user)
        
        # 根据组件类型返回相应数据
        if widget.widget_type == 'chart':
            # 返回图表数据
            return Response({
                'type': 'chart',
                'data': widget.config.get('data', []),
                'options': widget.config.get('options', {})
            })
        elif widget.widget_type == 'metric':
            # 返回指标数据
            return Response({
                'type': 'metric',
                'value': widget.config.get('value', 0),
                'label': widget.config.get('label', ''),
                'trend': widget.config.get('trend', 0)
            })
        else:
            return Response({
                'type': widget.widget_type,
                'data': widget.config
            })
            
    except DashboardWidget.DoesNotExist:
        return Response({'error': '组件不存在'}, status=status.HTTP_404_NOT_FOUND)