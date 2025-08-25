from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q, Sum
from django.db import transaction
from .models import PointsRecord, PointsTransaction, PointsReward, PointsRedemption
from .serializers import (
    PointsRecordSerializer, PointsTransactionSerializer, PointsTransactionCreateSerializer,
    PointsRewardSerializer, PointsRedemptionSerializer, PointsRedemptionCreateSerializer
)

class PointsRecordListView(generics.ListAPIView):
    serializer_class = PointsRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        record_type = self.request.query_params.get('record_type')
        
        queryset = PointsRecord.objects.filter(user=user)
        
        if record_type:
            queryset = queryset.filter(record_type=record_type)
            
        return queryset.order_by('-created_at')

class PointsTransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PointsTransactionCreateSerializer
        return PointsTransactionSerializer

    def get_queryset(self):
        user = self.request.user
        return PointsTransaction.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        import uuid
        transaction_id = str(uuid.uuid4())
        serializer.save(from_user=self.request.user, transaction_id=transaction_id)

class PointsRewardListView(generics.ListAPIView):
    serializer_class = PointsRewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointsReward.objects.filter(is_active=True, stock__gt=0).order_by('-created_at')

class PointsRedemptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PointsRedemptionCreateSerializer
        return PointsRedemptionSerializer

    def get_queryset(self):
        return PointsRedemption.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        reward = serializer.validated_data['reward']
        user = self.request.user
        
        # 检查用户积分是否足够
        if user.balance < reward.points_required:
            raise serializers.ValidationError("积分不足")
        
        # 检查库存
        if reward.stock <= 0:
            raise serializers.ValidationError("库存不足")
        
        # 扣除积分并减少库存
        with transaction.atomic():
            user.balance -= reward.points_required
            user.save()
            
            reward.stock -= 1
            reward.save()
            
            # 创建积分记录
            PointsRecord.objects.create(
                user=user,
                record_type='spent',
                amount=-reward.points_required,
                description=f"兑换奖励: {reward.name}"
            )
            
            serializer.save(user=user, points_spent=reward.points_required)

@api_view(['GET'])
def my_points_summary(request):
    """获取用户积分摘要"""
    user = request.user
    
    # 积分统计
    total_earned = PointsRecord.objects.filter(
        user=user, 
        record_type__in=['earned', 'bonus', 'transfer_in']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_spent = PointsRecord.objects.filter(
        user=user, 
        record_type__in=['spent', 'penalty', 'transfer_out']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # 最近记录
    recent_records = PointsRecord.objects.filter(user=user).order_by('-created_at')[:10]
    
    # 待处理的兑换
    pending_redemptions = PointsRedemption.objects.filter(
        user=user, 
        status='pending'
    ).count()
    
    return Response({
        'current_balance': float(user.balance) if hasattr(user, 'balance') else 0,
        'total_earned': abs(total_earned),
        'total_spent': abs(total_spent),
        'pending_redemptions': pending_redemptions,
        'recent_records': PointsRecordSerializer(recent_records, many=True).data
    })

@api_view(['POST'])
def transfer_points(request):
    """转账积分"""
    to_user_id = request.data.get('to_user')
    amount = request.data.get('amount')
    message = request.data.get('message', '')
    
    if not to_user_id or not amount:
        return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
    
    if amount <= 0:
        return Response({'error': '转账金额必须大于0'}, status=status.HTTP_400_BAD_REQUEST)
    
    from_user = request.user
    
    try:
        from apps.users.models import User
        to_user = User.objects.get(id=to_user_id)
    except User.DoesNotExist:
        return Response({'error': '目标用户不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    if from_user == to_user:
        return Response({'error': '不能转账给自己'}, status=status.HTTP_400_BAD_REQUEST)
    
    if from_user.balance < amount:
        return Response({'error': '积分余额不足'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 执行转账
    with transaction.atomic():
        from_user.balance -= amount
        to_user.balance += amount
        from_user.save()
        to_user.save()
        
        # 创建转账记录
        import uuid
        transaction_id = str(uuid.uuid4())
        
        points_transaction = PointsTransaction.objects.create(
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            message=message,
            transaction_id=transaction_id,
            status='completed'
        )
        
        # 创建积分记录
        PointsRecord.objects.create(
            user=from_user,
            record_type='transfer_out',
            amount=-amount,
            description=f"转账给 {to_user.username}: {message}"
        )
        
        PointsRecord.objects.create(
            user=to_user,
            record_type='transfer_in',
            amount=amount,
            description=f"来自 {from_user.username} 的转账: {message}"
        )
        
        from django.utils import timezone
        points_transaction.completed_at = timezone.now()
        points_transaction.save()
    
    return Response({
        'message': '转账成功',
        'transaction_id': transaction_id,
        'new_balance': float(from_user.balance)
    })

@api_view(['GET'])
def available_rewards(request):
    """获取可用奖励列表"""
    user = request.user
    user_balance = getattr(user, 'balance', 0)
    
    rewards = PointsReward.objects.filter(is_active=True, stock__gt=0)
    
    reward_data = []
    for reward in rewards:
        reward_info = PointsRewardSerializer(reward).data
        reward_info['can_afford'] = user_balance >= reward.points_required
        reward_data.append(reward_info)
    
    return Response({
        'user_balance': float(user_balance),
        'rewards': reward_data
    })