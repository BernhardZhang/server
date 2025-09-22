from rest_framework import serializers
from .models import (
    MeritRound, ContributionEvaluation, MeritCriteria, DetailedEvaluation,
    ProjectMeritCalculation, TaskMeritAssignment, PeerReview, MeritCalculationResult
)
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


class ProjectMeritCalculationSerializer(serializers.ModelSerializer):
    """项目功分计算序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    task_assignments_count = serializers.SerializerMethodField()
    peer_reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMeritCalculation
        fields = (
            'id', 'project', 'project_name', 'name', 'description', 'status',
            'total_project_value', 'calculation_start_date', 'calculation_end_date',
            'peer_review_deadline', 'created_by', 'created_by_name', 'created_at',
            'updated_at', 'task_assignments_count', 'peer_reviews_count'
        )
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_task_assignments_count(self, obj):
        return obj.task_assignments.count()

    def get_peer_reviews_count(self, obj):
        return obj.peer_reviews.count()


class TaskMeritAssignmentSerializer(serializers.ModelSerializer):
    """任务功分分配序列化器"""
    task_title = serializers.CharField(source='task.title', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    calculation_name = serializers.CharField(source='calculation.name', read_only=True)

    class Meta:
        model = TaskMeritAssignment
        fields = (
            'id', 'calculation', 'calculation_name', 'task', 'task_title',
            'user', 'user_name', 'task_percentage', 'role_weight',
            'planned_start_date', 'planned_end_date', 'actual_end_date',
            'time_coefficient', 'system_score', 'function_score', 'total_score',
            'created_at', 'updated_at'
        )
        read_only_fields = ('time_coefficient', 'system_score', 'total_score', 'created_at', 'updated_at')


class PeerReviewSerializer(serializers.ModelSerializer):
    """同行互评序列化器"""
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    reviewed_user_name = serializers.CharField(source='reviewed_user.username', read_only=True)
    calculation_name = serializers.CharField(source='calculation.name', read_only=True)

    class Meta:
        model = PeerReview
        fields = (
            'id', 'calculation', 'calculation_name', 'reviewer', 'reviewer_name',
            'reviewed_user', 'reviewed_user_name', 'score', 'work_quality_score',
            'collaboration_score', 'efficiency_score', 'innovation_score',
            'comment', 'is_anonymous', 'created_at', 'updated_at'
        )
        read_only_fields = ('reviewer', 'created_at', 'updated_at')

    def validate(self, attrs):
        reviewer = self.context['request'].user
        reviewed_user = attrs['reviewed_user']
        calculation = attrs['calculation']

        # 不能评价自己
        if reviewer == reviewed_user:
            raise serializers.ValidationError("不能评价自己")

        # 检查是否已经评价过
        if PeerReview.objects.filter(
            calculation=calculation,
            reviewer=reviewer,
            reviewed_user=reviewed_user
        ).exists():
            raise serializers.ValidationError("您已经评价过该用户")

        # 检查评价人是否是项目成员
        if not calculation.project.members.filter(id=reviewer.id).exists():
            raise serializers.ValidationError("您不是该项目的成员，无法进行评价")

        # 检查被评价用户是否是项目成员
        if not calculation.project.members.filter(id=reviewed_user.id).exists():
            raise serializers.ValidationError("被评价用户不是该项目的成员")

        return attrs


class MeritCalculationResultSerializer(serializers.ModelSerializer):
    """功分计算结果序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    calculation_name = serializers.CharField(source='calculation.name', read_only=True)
    project_name = serializers.CharField(source='calculation.project.name', read_only=True)

    class Meta:
        model = MeritCalculationResult
        fields = (
            'id', 'calculation', 'calculation_name', 'project_name', 'user', 'user_name',
            'total_system_score', 'total_peer_reviews_received', 'average_peer_review_score',
            'individual_points', 'total_team_points', 'function_score', 'final_score',
            'rank', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')