from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.AnalysisReportListCreateView.as_view(), name='analysis-report-list-create'),
    path('reports/<int:pk>/', views.AnalysisReportDetailView.as_view(), name='analysis-report-detail'),
    path('metrics/', views.DataMetricListView.as_view(), name='data-metric-list'),
    path('dashboard/statistics/', views.dashboard_statistics, name='dashboard-statistics'),
    path('user-performance/', views.user_performance_analysis, name='user-performance-analysis'),
    path('project-progress/', views.project_progress_analysis, name='project-progress-analysis'),
]