from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, F, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from rest_framework import serializers

from .models import (
    MeritRound, ContributionEvaluation, MeritCriteria, DetailedEvaluation,
    ProjectMeritCalculation, TaskMeritAssignment, PeerReview, MeritCalculationResult
)
from .serializers import (
    MeritRoundSerializer, ContributionEvaluationSerializer,
    ContributionEvaluationCreateSerializer, MeritCriteriaSerializer,
    EvaluationStatsSerializer, ProjectMeritSummarySerializer,
    ProjectMeritCalculationSerializer, TaskMeritAssignmentSerializer,
    PeerReviewSerializer, MeritCalculationResultSerializer
)


class ProjectMeritCalculationViewSet(viewsets.ModelViewSet):
    """项目功分计算管理"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        # 用户只能看到自己参与项目的功分计算
        return ProjectMeritCalculation.objects.filter(
            project__members=self.request.user
        ).select_related('project', 'created_by')

    def get_serializer_class(self):
        return ProjectMeritCalculationSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _calculate_time_coefficient(self, planned_end_date, actual_end_date, planned_start_date=None):
        """计算时效系数"""
        if not planned_end_date or not actual_end_date:
            return Decimal('1.00')

        # 计算提前/延迟天数
        days_diff = (actual_end_date - planned_end_date).days

        if days_diff <= -7:  # 提前7天以上
            return Decimal('1.30')
        elif days_diff <= -4:  # 提前4-6天
            return Decimal('1.30')
        elif days_diff <= -1:  # 提前1-3天
            return Decimal('1.20')
        elif days_diff == 0:  # 按时完成
            return Decimal('1.00')
        else:
            # 计算超时比例
            if planned_start_date:
                planned_duration = (planned_end_date - planned_start_date).days
            else:
                planned_duration = 30  # 默认30天

            if planned_duration <= 0:
                planned_duration = 30

            overtime_ratio = days_diff / planned_duration

            if overtime_ratio <= 0.1:  # 超时≤10%
                return Decimal('0.90')
            elif overtime_ratio <= 0.3:  # 10% < 超时≤30%
                return Decimal('0.70')
            else:  # 超时 > 30%
                return Decimal('0.50')

    def _calculate_project_merit_results(self, calculation_id):
        """计算项目的最终功分结果"""
        try:
            calculation = ProjectMeritCalculation.objects.get(id=calculation_id)
        except ProjectMeritCalculation.DoesNotExist:
            return []

        # 获取所有任务分配
        task_assignments = TaskMeritAssignment.objects.filter(calculation=calculation)

        # 按用户分组计算
        user_results = {}

        for assignment in task_assignments:
            user_id = assignment.user.id
            username = assignment.user.username

            if user_id not in user_results:
                user_results[user_id] = {
                    'user_id': user_id,
                    'username': username,
                    'total_system_score': Decimal('0.00'),
                    'assignments': [],
                }

            # 累加系统分
            user_results[user_id]['total_system_score'] += assignment.system_score
            user_results[user_id]['assignments'].append({
                'task_title': assignment.task.title,
                'task_percentage': assignment.task_percentage,
                'role_weight': assignment.role_weight,
                'time_coefficient': assignment.time_coefficient,
                'system_score': assignment.system_score
            })

        # 计算互评平均分和功分
        all_team_points = Decimal('0.00')
        for user_id in user_results:
            # 计算用户的互评平均分
            reviews = PeerReview.objects.filter(
                calculation_id=calculation_id,
                reviewed_user_id=user_id
            )

            if reviews.exists():
                avg_score = reviews.aggregate(avg_score=Avg('score'))['avg_score'] or 0
                review_count = reviews.count()
            else:
                avg_score = 0
                review_count = 0

            user_results[user_id]['average_peer_review_score'] = Decimal(str(avg_score))
            user_results[user_id]['review_count'] = review_count
            user_results[user_id]['individual_points'] = Decimal(str(avg_score))  # 个人积分等于互评平均分
            all_team_points += Decimal(str(avg_score))

        # 计算功分和最终得分
        final_results = []
        for user_id, result in user_results.items():
            # 计算功分得分：个人获得积分 ÷ 全队总积分 × 30分
            if all_team_points > 0:
                function_score = (result['individual_points'] / all_team_points) * Decimal('30.00')
            else:
                function_score = Decimal('0.00')

            final_score = result['total_system_score'] + function_score

            final_results.append({
                'user_id': user_id,
                'username': result['username'],
                'total_system_score': result['total_system_score'],
                'individual_points': result['individual_points'],
                'total_team_points': all_team_points,
                'function_score': function_score,
                'final_score': final_score,
                'average_peer_review_score': result['average_peer_review_score'],
                'review_count': result['review_count'],
                'assignments': result['assignments']
            })

        # 按最终得分排序
        final_results.sort(key=lambda x: x['final_score'], reverse=True)

        # 添加排名
        for rank, result in enumerate(final_results, 1):
            result['rank'] = rank

        return final_results

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """获取功分计算摘要"""
        calculation = self.get_object()

        # 基本信息
        summary = {
            'calculation_id': calculation.id,
            'calculation_name': calculation.name,
            'project_name': calculation.project.name,
            'status': calculation.status,
            'total_project_value': float(calculation.total_project_value),
            'created_at': calculation.created_at.isoformat(),
        }

        # 任务分配统计
        task_assignments = TaskMeritAssignment.objects.filter(calculation=calculation)
        summary['total_tasks'] = task_assignments.count()
        summary['total_participants'] = task_assignments.values('user').distinct().count()

        # 任务占比验证
        total_percentage = task_assignments.aggregate(
            total=Sum('task_percentage')
        )['total'] or 0
        summary['total_task_percentage'] = float(total_percentage)
        summary['percentage_valid'] = abs(float(total_percentage) - 100.0) < 0.01

        # 互评统计
        peer_reviews = PeerReview.objects.filter(calculation=calculation)
        summary['total_peer_reviews'] = peer_reviews.count()
        summary['average_peer_score'] = float(peer_reviews.aggregate(
            avg=Avg('score')
        )['avg'] or 0)

        # 结果统计
        results = MeritCalculationResult.objects.filter(calculation=calculation)
        if results.exists():
            summary['results_calculated'] = True
            summary['highest_score'] = float(results.first().final_score)
            summary['lowest_score'] = float(results.last().final_score)
            summary['average_final_score'] = float(results.aggregate(
                avg=Avg('final_score')
            )['avg'] or 0)
        else:
            summary['results_calculated'] = False

        return Response(summary)

    @action(detail=True, methods=['post'])
    def calculate(self, request, pk=None):
        """执行功分计算"""
        calculation = self.get_object()

        # 检查任务占比总和是否为100%
        task_assignments = TaskMeritAssignment.objects.filter(calculation=calculation)
        total_percentage = task_assignments.aggregate(
            total=Sum('task_percentage')
        )['total'] or 0

        if abs(float(total_percentage) - 100.0) > 0.01:
            return Response({
                'error': f'任务占比总和必须为100%，当前为{float(total_percentage):.2f}%'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 重新计算所有任务分配的分数
        for assignment in task_assignments:
            # 重新计算时效系数
            if assignment.actual_end_date:
                assignment.time_coefficient = self._calculate_time_coefficient(
                    assignment.planned_end_date,
                    assignment.actual_end_date,
                    assignment.planned_start_date
                )

            # 重新计算系统分
            base_score = calculation.total_project_value * (assignment.task_percentage / 100)
            assignment.system_score = base_score * assignment.role_weight * assignment.time_coefficient

            # 重新计算总分
            assignment.total_score = assignment.system_score + assignment.function_score
            assignment.save()

        # 计算最终结果
        results = self._calculate_project_merit_results(calculation.id)

        # 清除旧结果并保存新结果
        MeritCalculationResult.objects.filter(calculation=calculation).delete()

        saved_results = []
        for result in results:
            merit_result = MeritCalculationResult.objects.create(
                calculation=calculation,
                user_id=result['user_id'],
                total_system_score=result['total_system_score'],
                total_peer_reviews_received=result['review_count'],
                average_peer_review_score=result['average_peer_review_score'],
                individual_points=result['individual_points'],
                total_team_points=result['total_team_points'],
                function_score=result['function_score'],
                final_score=result['final_score'],
                rank=result['rank']
            )
            saved_results.append(merit_result)

        # 更新计算状态
        calculation.status = 'completed'
        calculation.save()

        return Response({
            'message': '功分计算完成',
            'results_count': len(results),
            'results': MeritCalculationResultSerializer(saved_results, many=True).data
        })

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """获取计算结果"""
        calculation = self.get_object()
        results = MeritCalculationResult.objects.filter(
            calculation=calculation
        ).select_related('user').order_by('rank')

        serializer = MeritCalculationResultSerializer(results, many=True)
        return Response(serializer.data)


class TaskMeritAssignmentViewSet(viewsets.ModelViewSet):
    """任务功分分配管理"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['calculation', 'task', 'user']
    ordering = ['-total_score']

    def get_queryset(self):
        return TaskMeritAssignment.objects.filter(
            calculation__project__members=self.request.user
        ).select_related('calculation', 'task', 'user')

    def get_serializer_class(self):
        return TaskMeritAssignmentSerializer

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建任务分配"""
        data = request.data
        calculation_id = data.get('calculation_id')
        assignments = data.get('assignments', [])

        try:
            calculation = ProjectMeritCalculation.objects.get(
                id=calculation_id,
                project__members=request.user
            )
        except ProjectMeritCalculation.DoesNotExist:
            return Response({
                'error': '功分计算不存在或无权限'
            }, status=status.HTTP_404_NOT_FOUND)

        # 验证任务占比总和
        total_percentage = sum(Decimal(str(assignment.get('task_percentage', 0))) for assignment in assignments)
        if abs(float(total_percentage) - 100.0) > 0.01:
            return Response({
                'error': f'任务占比总和必须为100%，当前为{float(total_percentage):.2f}%'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 批量创建
        created_assignments = []
        for assignment_data in assignments:
            assignment_data['calculation'] = calculation_id
            serializer = TaskMeritAssignmentSerializer(data=assignment_data)
            if serializer.is_valid():
                assignment = serializer.save()
                created_assignments.append(assignment)
            else:
                return Response({
                    'error': f'任务分配数据无效: {serializer.errors}'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'成功创建{len(created_assignments)}个任务分配',
            'assignments': TaskMeritAssignmentSerializer(created_assignments, many=True).data
        })


class PeerReviewViewSet(viewsets.ModelViewSet):
    """同行互评管理"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['calculation', 'reviewer', 'reviewed_user']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        return PeerReview.objects.filter(
            Q(reviewer=user) | Q(reviewed_user=user),
            calculation__project__members=user
        ).select_related('calculation', 'reviewer', 'reviewed_user')

    def get_serializer_class(self):
        return PeerReviewSerializer

    def perform_create(self, serializer):
        # 防止自评
        if serializer.validated_data['reviewed_user'] == self.request.user:
            raise serializers.ValidationError('不能评价自己')
        serializer.save(reviewer=self.request.user)

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """我的评价记录"""
        calculation_id = request.query_params.get('calculation_id')

        queryset = PeerReview.objects.filter(reviewer=request.user)
        if calculation_id:
            queryset = queryset.filter(calculation_id=calculation_id)

        queryset = queryset.select_related('reviewed_user', 'calculation')
        serializer = PeerReviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """待评价的用户列表"""
        calculation_id = request.query_params.get('calculation_id')

        if not calculation_id:
            return Response({
                'error': '请提供calculation_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            calculation = ProjectMeritCalculation.objects.get(
                id=calculation_id,
                project__members=request.user
            )
        except ProjectMeritCalculation.DoesNotExist:
            return Response({
                'error': '功分计算不存在或无权限'
            }, status=status.HTTP_404_NOT_FOUND)

        # 获取项目所有成员（除了自己）
        project_members = calculation.project.members.exclude(id=request.user.id)

        # 获取已评价的用户
        reviewed_users = PeerReview.objects.filter(
            calculation=calculation,
            reviewer=request.user
        ).values_list('reviewed_user_id', flat=True)

        # 待评价的用户
        pending_users = project_members.exclude(id__in=reviewed_users)

        return Response({
            'calculation_id': calculation.id,
            'calculation_name': calculation.name,
            'total_members': project_members.count(),
            'reviewed_count': len(reviewed_users),
            'pending_count': pending_users.count(),
            'pending_users': [
                {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
                for user in pending_users
            ]
        })


class MeritCalculationResultViewSet(viewsets.ReadOnlyModelViewSet):
    """功分计算结果查看"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['calculation', 'user']
    ordering = ['rank']

    def get_queryset(self):
        return MeritCalculationResult.objects.filter(
            calculation__project__members=self.request.user
        ).select_related('calculation', 'user')

    def get_serializer_class(self):
        return MeritCalculationResultSerializer


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

    # 功分计算统计
    merit_calculations = ProjectMeritCalculation.objects.filter(
        project__members=user
    )

    # 统计数据
    stats = {
        'active_round': MeritRoundSerializer(active_round).data if active_round else None,
        'total_given': given_evaluations.count(),
        'total_received': received_evaluations.count(),
        'current_round_given': given_evaluations_current.count(),
        'current_round_received': received_evaluations_current.count(),
        'average_score_received': received_evaluations.aggregate(
            avg=Avg('contribution_score'))['avg'] or 0,
        'merit_calculations_count': merit_calculations.count(),
        'completed_calculations': merit_calculations.filter(status='completed').count(),
        'recent_evaluations_given': ContributionEvaluationSerializer(
            given_evaluations.order_by('-created_at')[:5], many=True
        ).data,
        'recent_evaluations_received': ContributionEvaluationSerializer(
            received_evaluations.order_by('-created_at')[:5], many=True
        ).data,
    }

    return Response(stats)