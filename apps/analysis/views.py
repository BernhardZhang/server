from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q, Count, Avg
from .models import AnalysisReport, DataMetric
from .serializers import AnalysisReportSerializer, AnalysisReportCreateSerializer, DataMetricSerializer

class AnalysisReportListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnalysisReportCreateSerializer
        return AnalysisReportSerializer

    def get_queryset(self):
        user = self.request.user
        report_type = self.request.query_params.get('report_type')
        
        queryset = AnalysisReport.objects.filter(creator=user)
        
        if report_type:
            queryset = queryset.filter(report_type=report_type)
            
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class AnalysisReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AnalysisReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AnalysisReport.objects.filter(creator=self.request.user)

class DataMetricListView(generics.ListAPIView):
    serializer_class = DataMetricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        metric_type = self.request.query_params.get('metric_type')
        queryset = DataMetric.objects.all()
        
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
            
        return queryset.order_by('-timestamp')

@api_view(['GET'])
def dashboard_statistics(request):
    """获取仪表板统计数据"""
    from apps.users.models import User
    from apps.projects.models import Project
    from apps.voting.models import VotingRound, Vote
    
    # 基础统计
    user_count = User.objects.count()
    project_count = Project.objects.count()
    voting_round_count = VotingRound.objects.count()
    vote_count = Vote.objects.count()
    
    # 项目状态分布
    project_status_stats = Project.objects.values('status').annotate(count=Count('id'))
    
    # 投票统计
    recent_votes = Vote.objects.select_related('user', 'target_user', 'target_project').order_by('-created_at')[:10]
    
    return Response({
        'basic_stats': {
            'user_count': user_count,
            'project_count': project_count,
            'voting_round_count': voting_round_count,
            'vote_count': vote_count
        },
        'project_status_distribution': list(project_status_stats),
        'recent_votes': [
            {
                'id': vote.id,
                'voter': vote.user.username,
                'target': vote.target_user.username if vote.target_user else vote.target_project.name,
                'score': vote.score,
                'created_at': vote.created_at
            } for vote in recent_votes
        ]
    })

@api_view(['GET'])
def user_performance_analysis(request):
    """用户绩效分析"""
    from django.db.models import Sum, Avg
    from apps.voting.models import Vote
    from apps.users.models import User
    
    user_stats = User.objects.annotate(
        total_votes_received=Count('votes_received'),
        avg_score=Avg('votes_received__score'),
        total_votes_cast=Count('votes_cast')
    ).order_by('-total_votes_received')[:20]
    
    return Response({
        'top_performers': [
            {
                'username': user.username,
                'total_votes_received': user.total_votes_received,
                'average_score': float(user.avg_score) if user.avg_score else 0,
                'total_votes_cast': user.total_votes_cast,
                'balance': float(user.balance)
            } for user in user_stats
        ]
    })

@api_view(['GET'])
def project_progress_analysis(request):
    """项目进度分析"""
    from apps.projects.models import Project
    
    projects = Project.objects.annotate(
        member_count=Count('members'),
        vote_count=Count('votes_received')
    ).order_by('-created_at')[:20]
    
    return Response({
        'projects': [
            {
                'name': project.name,
                'status': project.status,
                'member_count': project.member_count,
                'vote_count': project.vote_count,
                'created_at': project.created_at,
                'progress_percentage': project.calculated_progress
            } for project in projects
        ]
    })