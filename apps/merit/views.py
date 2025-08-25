from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import MeritRound, ContributionEvaluation, MeritCriteria, DetailedEvaluation
from .serializers import (
    MeritRoundSerializer, ContributionEvaluationSerializer, 
    ContributionEvaluationCreateSerializer, MeritCriteriaSerializer,
    EvaluationStatsSerializer, ProjectMeritSummarySerializer
)


class MeritRoundViewSet(viewsets.ModelViewSet):
    """功分互评轮次管理"""
    queryset = MeritRound.objects.all().order_by('-created_at')
    serializer_class = MeritRoundSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取当前活跃的评价轮次"""
        active_round = MeritRound.objects.filter(is_active=True).first()
        if active_round:
            serializer = self.get_serializer(active_round)
            return Response(serializer.data)
        return Response({'detail': '暂无活跃的评价轮次'}, status=status.HTTP_404_NOT_FOUND)


class ContributionEvaluationViewSet(viewsets.ModelViewSet):
    """贡献度评价管理"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'merit_round', 'evaluator', 'evaluated_user']
    search_fields = ['comment', 'evaluated_user__username', 'project__name']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # 用户只能看到自己参与的评价（作为评价人或被评价人）
        return ContributionEvaluation.objects.filter(
            Q(evaluator=user) | Q(evaluated_user=user)
        ).select_related('evaluator', 'evaluated_user', 'project', 'merit_round')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ContributionEvaluationCreateSerializer
        return ContributionEvaluationSerializer

    @action(detail=False, methods=['get'])
    def my_given(self, request):
        """我给出的评价"""
        merit_round_id = request.query_params.get('merit_round')
        project_id = request.query_params.get('project')
        
        queryset = ContributionEvaluation.objects.filter(evaluator=request.user)
        
        if merit_round_id:
            queryset = queryset.filter(merit_round_id=merit_round_id)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        queryset = queryset.select_related('evaluated_user', 'project', 'merit_round')
        serializer = ContributionEvaluationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_received(self, request):
        """我收到的评价"""
        merit_round_id = request.query_params.get('merit_round')
        project_id = request.query_params.get('project')
        
        queryset = ContributionEvaluation.objects.filter(evaluated_user=request.user)
        
        if merit_round_id:
            queryset = queryset.filter(merit_round_id=merit_round_id)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        queryset = queryset.select_related('evaluator', 'project', 'merit_round')
        serializer = ContributionEvaluationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """评价统计"""
        user = request.user
        merit_round_id = request.query_params.get('merit_round')
        
        base_queryset = ContributionEvaluation.objects.all()
        if merit_round_id:
            base_queryset = base_queryset.filter(merit_round_id=merit_round_id)
        
        # 统计数据
        given_evaluations = base_queryset.filter(evaluator=user)
        received_evaluations = base_queryset.filter(evaluated_user=user)
        
        stats = {
            'total_evaluations': base_queryset.count(),
            'given_evaluations': given_evaluations.count(),
            'received_evaluations': received_evaluations.count(),
            'average_score_given': given_evaluations.aggregate(
                avg=Avg('contribution_score'))['avg'] or 0,
            'average_score_received': received_evaluations.aggregate(
                avg=Avg('contribution_score'))['avg'] or 0,
        }
        
        # 获取得分最高的用户
        top_contributors = base_queryset.values('evaluated_user__username').annotate(
            avg_score=Avg('contribution_score'),
            evaluation_count=Count('id')
        ).filter(evaluation_count__gte=3).order_by('-avg_score')[:5]
        
        stats['top_contributors'] = list(top_contributors)
        
        serializer = EvaluationStatsSerializer(stats)
        return Response(serializer.data)


class MeritCriteriaViewSet(viewsets.ModelViewSet):
    """评价标准管理"""
    queryset = MeritCriteria.objects.filter(is_active=True).order_by('name')
    serializer_class = MeritCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['name']


@api_view(['GET'])
def project_merit_summary(request, project_id):
    """获取项目的功分总结"""
    if not request.user.is_authenticated:
        return Response({'detail': '认证信息无效'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        from apps.projects.models import Project
        project = Project.objects.get(id=project_id)
        
        # 检查用户是否是项目成员
        if not project.members.filter(id=request.user.id).exists():
            return Response({'detail': '您不是该项目的成员'}, status=status.HTTP_403_FORBIDDEN)
        
        merit_round_id = request.query_params.get('merit_round')
        
        # 获取项目的所有评价
        evaluations = ContributionEvaluation.objects.filter(project=project)
        if merit_round_id:
            evaluations = evaluations.filter(merit_round_id=merit_round_id)
        
        # 统计数据
        total_evaluations = evaluations.count()
        if total_evaluations == 0:
            return Response({
                'project_id': project.id,
                'project_name': project.name,
                'total_evaluations': 0,
                'average_score': 0,
                'participant_count': 0,
                'top_performer': None,
                'evaluation_completion_rate': 0
            })
        
        average_score = evaluations.aggregate(avg=Avg('contribution_score'))['avg'] or 0
        
        # 参与评价的用户数量
        participant_count = evaluations.values('evaluated_user').distinct().count()
        
        # 得分最高的用户
        top_performer_data = evaluations.values('evaluated_user__username').annotate(
            avg_score=Avg('contribution_score'),
            evaluation_count=Count('id')
        ).order_by('-avg_score').first()
        
        top_performer = {
            'username': top_performer_data['evaluated_user__username'],
            'average_score': top_performer_data['avg_score'],
            'evaluation_count': top_performer_data['evaluation_count']
        } if top_performer_data else None
        
        # 评价完成率（假设每个成员都应该被其他成员评价）
        project_member_count = project.members.count()
        expected_evaluations = project_member_count * (project_member_count - 1)  # 不包括自评
        completion_rate = (total_evaluations / expected_evaluations * 100) if expected_evaluations > 0 else 0
        
        summary = {
            'project_id': project.id,
            'project_name': project.name,
            'total_evaluations': total_evaluations,
            'average_score': round(average_score, 2),
            'participant_count': participant_count,
            'top_performer': top_performer,
            'evaluation_completion_rate': round(completion_rate, 2)
        }
        
        serializer = ProjectMeritSummarySerializer(summary)
        return Response(serializer.data)
        
    except Project.DoesNotExist:
        return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def merit_dashboard(request):
    """功分互评仪表板数据"""
    if not request.user.is_authenticated:
        return Response({'detail': '认证信息无效'}, status=status.HTTP_401_UNAUTHORIZED)
    
    user = request.user
    
    # 获取活跃轮次
    active_round = MeritRound.objects.filter(is_active=True).first()
    
    # 基础统计
    given_evaluations = ContributionEvaluation.objects.filter(evaluator=user)
    received_evaluations = ContributionEvaluation.objects.filter(evaluated_user=user)
    
    if active_round:
        given_evaluations_current = given_evaluations.filter(merit_round=active_round)
        received_evaluations_current = received_evaluations.filter(merit_round=active_round)
    else:
        given_evaluations_current = given_evaluations.none()
        received_evaluations_current = received_evaluations.none()
    
    # 统计数据
    stats = {
        'active_round': MeritRoundSerializer(active_round).data if active_round else None,
        'total_given': given_evaluations.count(),
        'total_received': received_evaluations.count(),
        'current_round_given': given_evaluations_current.count(),
        'current_round_received': received_evaluations_current.count(),
        'average_score_received': received_evaluations.aggregate(
            avg=Avg('contribution_score'))['avg'] or 0,
        'recent_evaluations_given': ContributionEvaluationSerializer(
            given_evaluations.order_by('-created_at')[:5], many=True
        ).data,
        'recent_evaluations_received': ContributionEvaluationSerializer(
            received_evaluations.order_by('-created_at')[:5], many=True
        ).data,
    }
    
    return Response(stats)