from rest_framework import serializers
from .models import PointsRecord, PointsTransaction, PointsReward, PointsRedemption

class PointsRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PointsRecord
        fields = ('id', 'user', 'user_name', 'record_type', 'amount', 'description', 
                 'related_vote', 'related_project', 'created_at')

class PointsTransactionSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.username', read_only=True)
    to_user_name = serializers.CharField(source='to_user.username', read_only=True)

    class Meta:
        model = PointsTransaction
        fields = ('id', 'from_user', 'from_user_name', 'to_user', 'to_user_name', 
                 'amount', 'message', 'status', 'transaction_id', 'created_at', 'completed_at')

class PointsTransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsTransaction
        fields = ('to_user', 'amount', 'message')

class PointsRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsReward
        fields = ('id', 'name', 'description', 'points_required', 'reward_type', 
                 'is_active', 'stock', 'image', 'created_at')

class PointsRedemptionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    reward_name = serializers.CharField(source='reward.name', read_only=True)

    class Meta:
        model = PointsRedemption
        fields = ('id', 'user', 'user_name', 'reward', 'reward_name', 'points_spent', 
                 'status', 'delivery_info', 'notes', 'created_at', 'processed_at')

class PointsRedemptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsRedemption
        fields = ('reward', 'delivery_info')