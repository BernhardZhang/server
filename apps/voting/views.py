from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from .models import VotingRound, Vote, ContributionEvaluation, SelfEvaluation
from .serializers import VotingRoundSerializer, VoteSerializer, VoteCreateSerializer, ContributionEvaluationSerializer, ContributionEvaluationCreateSerializer, SelfEvaluationSerializer, SelfEvaluationCreateSerializer

# 允许所有用户查看投票轮次
class VotingRoundListCreateView(generics.ListCreateAPIView):
    serializer_class = VotingRoundSerializer
    
    def get_permissions(self):
        # 只有认证用户可以创建投票轮次
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        # 所有用户可以查看投票轮次
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        return VotingRound.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        # 创建新轮次时停用所有其他轮次
        VotingRound.objects.filter(is_active=True).update(is_active=False)
        serializer.save()

# 允许所有用户查看活跃投票轮次
class ActiveVotingRoundView(generics.RetrieveAPIView):
    serializer_class = VotingRoundSerializer

    def get_permissions(self):
        return [permissions.AllowAny()]

    def get_object(self):
        active_round = VotingRound.objects.filter(is_active=True).first()
        if not active_round:
            # 如果没有活跃轮次，返回None将导致404
            return None
        return active_round
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response(
                {'error': '没有找到活跃的投票轮次'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@api_view(['POST'])
def activate_round(request, round_id):
    """激活指定的投票轮次"""
    try:
        # 停用所有轮次
        VotingRound.objects.filter(is_active=True).update(is_active=False)
        
        # 激活指定轮次
        round_obj = VotingRound.objects.get(id=round_id)
        round_obj.is_active = True
        round_obj.save()
        
        serializer = VotingRoundSerializer(round_obj)
        return Response(serializer.data)
    except VotingRound.DoesNotExist:
        return Response(
            {'error': '投票轮次不存在'}, 
            status=status.HTTP_404_NOT_FOUND
        )

class VoteListCreateView(generics.ListCreateAPIView):
    serializer_class = VoteSerializer
    
    def get_permissions(self):
        # 只有认证用户可以创建投票
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        # 所有用户可以查看投票
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return Vote.objects.filter(voting_round=voting_round).select_related(
                'voter', 'voted_user'
            ).order_by('-created_at')
        return Vote.objects.select_related(
            'voter', 'voted_user'
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VoteCreateSerializer
        return VoteSerializer
    
    def perform_create(self, serializer):
        # 检查用户是否已经给该用户投过票
        voting_round = serializer.validated_data['voting_round']
        voted_user = serializer.validated_data['voted_user']
        
        existing_vote = Vote.objects.filter(
            voting_round=voting_round,
            voter=self.request.user,
            voted_user=voted_user
        ).exists()
        
        if existing_vote:
            raise serializers.ValidationError("您已经给该用户投过票了")
        
        serializer.save(voter=self.request.user)

class MyVotesView(generics.ListAPIView):
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return Vote.objects.filter(
                voting_round=voting_round,
                voter=self.request.user
            ).select_related('voter', 'voted_user').order_by('-created_at')
        return Vote.objects.filter(voter=self.request.user).select_related(
            'voter', 'voted_user'
        ).order_by('-created_at')

class VotesReceivedView(generics.ListAPIView):
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return Vote.objects.filter(
                voting_round=voting_round,
                voted_user=self.request.user
            ).select_related('voter', 'voted_user').order_by('-created_at')
        return Vote.objects.filter(voted_user=self.request.user).select_related(
            'voter', 'voted_user'
        ).order_by('-created_at')

@api_view(['GET'])
def my_votes(request):
    voting_round_id = request.query_params.get('voting_round')
    votes = Vote.objects.filter(voter=request.user)
    
    if voting_round_id:
        votes = votes.filter(voting_round_id=voting_round_id)
    
    serializer = VoteSerializer(votes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def votes_received(request):
    voting_round_id = request.query_params.get('voting_round')
    votes = Vote.objects.filter(
        Q(target_user=request.user) | Q(target_project__members=request.user)
    ).distinct()
    
    if voting_round_id:
        votes = votes.filter(voting_round_id=voting_round_id)
    
    serializer = VoteSerializer(votes, many=True)
    return Response(serializer.data)

class ContributionEvaluationListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        # 只有认证用户可以创建评估
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        # 所有用户可以查看评估
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return ContributionEvaluation.objects.filter(
                voting_round=voting_round
            ).select_related(
                'evaluator', 'evaluated_user', 'voting_round'
            ).prefetch_related(
                'criteria_scores'
            ).order_by('-created_at')
        return ContributionEvaluation.objects.select_related(
            'evaluator', 'evaluated_user', 'voting_round'
        ).prefetch_related(
            'criteria_scores'
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContributionEvaluationCreateSerializer
        return ContributionEvaluationSerializer
    
    def perform_create(self, serializer):
        # 检查用户是否已经给该用户评估过
        voting_round = serializer.validated_data['voting_round']
        evaluated_user = serializer.validated_data['evaluated_user']
        
        existing_evaluation = ContributionEvaluation.objects.filter(
            voting_round=voting_round,
            evaluator=self.request.user,
            evaluated_user=evaluated_user
        ).exists()
        
        if existing_evaluation:
            raise serializers.ValidationError("您已经给该用户评估过了")
        
        serializer.save(evaluator=self.request.user)

class MyEvaluationsView(generics.ListAPIView):
    serializer_class = ContributionEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return ContributionEvaluation.objects.filter(
                voting_round=voting_round,
                evaluator=self.request.user
            ).select_related(
                'evaluator', 'evaluated_user', 'voting_round'
            ).prefetch_related(
                'criteria_scores'
            ).order_by('-created_at')
        return ContributionEvaluation.objects.filter(
            evaluator=self.request.user
        ).select_related(
            'evaluator', 'evaluated_user', 'voting_round'
        ).prefetch_related(
            'criteria_scores'
        ).order_by('-created_at')

class SelfEvaluationListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        # 只有认证用户可以创建自我评估
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        # 所有用户可以查看自我评估
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        voting_round = self.request.query_params.get('voting_round', None)
        if voting_round:
            return SelfEvaluation.objects.filter(
                voting_round=voting_round
            ).select_related(
                'user', 'voting_round'
            ).prefetch_related(
                'criteria_scores'
            ).order_by('-created_at')
        return SelfEvaluation.objects.select_related(
            'user', 'voting_round'
        ).prefetch_related(
            'criteria_scores'
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SelfEvaluationCreateSerializer
        return SelfEvaluationSerializer
    
    def perform_create(self, serializer):
        # 检查用户是否已经提交过自我评估
        voting_round = serializer.validated_data['voting_round']
        
        existing_evaluation = SelfEvaluation.objects.filter(
            voting_round=voting_round,
            user=self.request.user
        ).exists()
        
        if existing_evaluation:
            raise serializers.ValidationError("您已经提交过自我评估了")
        
        serializer.save(user=self.request.user)

class VoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """投票详细视图 - 支持查看、编辑、删除"""
    serializer_class = VoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # 用户只能操作自己的投票
        return Vote.objects.filter(voter=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return VoteCreateSerializer
        return VoteSerializer
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法修改投票'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已支付（如果已支付则不能修改）
        if instance.is_paid:
            return Response(
                {'error': '已支付的投票无法修改'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法删除投票'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已支付（如果已支付则不能删除）
        if instance.is_paid:
            return Response(
                {'error': '已支付的投票无法删除'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)

class ContributionEvaluationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """贡献评价详细视图 - 支持查看、编辑、删除"""
    serializer_class = ContributionEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # 用户只能操作自己创建的评价
        return ContributionEvaluation.objects.filter(evaluator=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ContributionEvaluationCreateSerializer
        return ContributionEvaluationSerializer
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法修改评价'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否在创建后24小时内
        time_diff = timezone.now() - instance.created_at
        if time_diff.total_seconds() > 24 * 3600:  # 24小时
            return Response(
                {'error': '评价创建超过24小时，无法修改'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法删除评价'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否在创建后24小时内
        time_diff = timezone.now() - instance.created_at
        if time_diff.total_seconds() > 24 * 3600:  # 24小时
            return Response(
                {'error': '评价创建超过24小时，无法删除'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)

class SelfEvaluationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """自评详细视图 - 支持查看、编辑、删除"""
    serializer_class = SelfEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # 用户只能操作自己的自评
        return SelfEvaluation.objects.filter(investor=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SelfEvaluationCreateSerializer
        return SelfEvaluationSerializer
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法修改自评'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已批准（已批准的不能修改）
        if instance.is_approved:
            return Response(
                {'error': '已批准的自评无法修改'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 检查投票轮次是否仍然活跃
        if not instance.voting_round.is_active:
            return Response(
                {'error': '投票轮次已结束，无法删除自评'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已批准（已批准的不能删除）
        if instance.is_approved:
            return Response(
                {'error': '已批准的自评无法删除'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)