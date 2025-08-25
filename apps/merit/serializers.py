from rest_framework import serializers
from .models import MeritRound, ContributionEvaluation, MeritCriteria, DetailedEvaluation
from django.contrib.auth import get_user_model

User = get_user_model()


class MeritRoundSerializer(serializers.ModelSerializer):
    """功分互评轮次序列化器"""
    
    class Meta:
        model = MeritRound
        fields = (
            'id', 'name', 'description', 'start_time', 'end_time', 
            'is_active', 'created_at'
        )


class MeritCriteriaSerializer(serializers.ModelSerializer):
    """评价标准序列化器"""
    
    class Meta:
        model = MeritCriteria
        fields = (
            'id', 'name', 'description', 'weight', 'is_active', 'created_at'
        )


class DetailedEvaluationSerializer(serializers.ModelSerializer):
    """详细评价序列化器"""
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    
    class Meta:
        model = DetailedEvaluation
        fields = (
            'id', 'criteria', 'criteria_name', 'score', 'comment'
        )


class ContributionEvaluationSerializer(serializers.ModelSerializer):
    """贡献评价序列化器（查看用）"""
    evaluator_name = serializers.CharField(source='evaluator.username', read_only=True)
    evaluated_user_name = serializers.CharField(source='evaluated_user.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    merit_round_name = serializers.CharField(source='merit_round.name', read_only=True)
    detailed_evaluations = DetailedEvaluationSerializer(many=True, read_only=True)
    
    class Meta:
        model = ContributionEvaluation
        fields = (
            'id', 'evaluator', 'evaluator_name', 'evaluated_user', 
            'evaluated_user_name', 'project', 'project_name', 
            'merit_round', 'merit_round_name', 'contribution_score', 
            'comment', 'detailed_evaluations', 'created_at', 'updated_at'
        )
        read_only_fields = ('evaluator', 'created_at', 'updated_at')


class ContributionEvaluationCreateSerializer(serializers.ModelSerializer):
    """贡献评价序列化器（创建用）"""
    detailed_scores = serializers.DictField(
        child=serializers.IntegerField(min_value=0, max_value=100),
        required=False,
        help_text="各项标准的详细分数，格式：{criteria_id: score}"
    )
    
    class Meta:
        model = ContributionEvaluation
        fields = (
            'evaluated_user', 'project', 'merit_round', 
            'contribution_score', 'comment', 'detailed_scores'
        )
    
    def validate(self, attrs):
        evaluator = self.context['request'].user
        evaluated_user = attrs['evaluated_user']
        project = attrs['project']
        merit_round = attrs['merit_round']
        
        # 不能评价自己
        if evaluator == evaluated_user:
            raise serializers.ValidationError("不能评价自己")
        
        # 检查评价轮次是否活跃
        if not merit_round.is_active:
            raise serializers.ValidationError("该评价轮次未开放")
        
        # 检查是否已经评价过
        if ContributionEvaluation.objects.filter(
            evaluator=evaluator,
            evaluated_user=evaluated_user,
            project=project,
            merit_round=merit_round
        ).exists():
            raise serializers.ValidationError("您已经评价过该用户在此项目中的贡献")
        
        # 检查被评价用户是否是项目成员
        if not project.members.filter(id=evaluated_user.id).exists():
            raise serializers.ValidationError("被评价用户不是该项目的成员")
        
        # 检查评价人是否是项目成员
        if not project.members.filter(id=evaluator.id).exists():
            raise serializers.ValidationError("您不是该项目的成员，无法进行评价")
        
        return attrs
    
    def create(self, validated_data):
        detailed_scores = validated_data.pop('detailed_scores', {})
        validated_data['evaluator'] = self.context['request'].user
        
        evaluation = super().create(validated_data)
        
        # 创建详细评价记录
        for criteria_id, score in detailed_scores.items():
            try:
                criteria = MeritCriteria.objects.get(id=criteria_id, is_active=True)
                DetailedEvaluation.objects.create(
                    base_evaluation=evaluation,
                    criteria=criteria,
                    score=score
                )
            except MeritCriteria.DoesNotExist:
                continue
        
        return evaluation


class EvaluationStatsSerializer(serializers.Serializer):
    """评价统计序列化器"""
    total_evaluations = serializers.IntegerField()
    given_evaluations = serializers.IntegerField()
    received_evaluations = serializers.IntegerField()
    average_score_given = serializers.FloatField()
    average_score_received = serializers.FloatField()
    top_contributors = serializers.ListField()
    
    
class ProjectMeritSummarySerializer(serializers.Serializer):
    """项目功分总结序列化器"""
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    total_evaluations = serializers.IntegerField()
    average_score = serializers.FloatField()
    participant_count = serializers.IntegerField()
    top_performer = serializers.DictField()
    evaluation_completion_rate = serializers.FloatField()