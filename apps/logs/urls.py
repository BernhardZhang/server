from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    # 项目日志
    path('projects/', views.ProjectLogListView.as_view(), name='project-logs'),

    # 任务日志
    path('tasks/', views.TaskLogListView.as_view(), name='task-logs'),

    # 任务用户日志
    path('user-logs/', views.TaskUserLogListCreateView.as_view(), name='task-user-logs'),
    path('user-logs/<int:pk>/', views.TaskUserLogDetailView.as_view(), name='task-user-log-detail'),

    # 系统日志
    path('system/', views.SystemLogListView.as_view(), name='system-logs'),

    # 统计和概览
    path('statistics/', views.log_statistics, name='log-statistics'),
    path('recent/', views.recent_logs, name='recent-logs'),
]