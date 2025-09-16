from rest_framework import serializers
from .models import VotingRound, Vote, ContributionEvaluation, SelfEvaluation, RatingSession, Rating

class VotingRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = VotingRound
        fields = ('id', 'name', 'description', 'start_time', 'end_time', 'is_active', 'is_self_evaluation_open', 'max_self_investment', 'created_at')

class VoteSerializer(serializers.ModelSerializer):
    voter_name = serializers.CharField(source='voter.username', read_only=True)
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Vote
        fields = ('id', 'voter', 'voter_name', 'target_user', 'target_project', 'target_name', 'voting_round', 'amount', 'vote_type', 'is_paid', 'created_at')

    def get_target_name(self, obj):
        if obj.target_user:
            return obj.target_user.username
        elif obj.target_project:
            return obj.target_project.name
        return None

class VoteCreateSerializer(serializers.ModelSerializer):
    voting_round = serializers.PrimaryKeyRelatedField(
        queryset=VotingRound.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Vote
        fields = ('target_user', 'target_project', 'voting_round', 'amount', 'vote_type')

    def validate(self, data):
        target_user = data.get('target_user')
        target_project = data.get('target_project')

        # 确保只能选择一个目标
        if target_user and target_project:
            raise serializers.ValidationError("不能同时投票给用户和项目")
        if not target_user and not target_project:
            raise serializers.ValidationError("必须选择投票目标")

        # 检查投票类型规则（只有在创建时设置默认值）
        voter = self.context['request'].user
        if target_user == voter:
            data['vote_type'] = 'self'
            # 只有在创建新投票且没有指定金额时才设置默认值
            if not self.instance and 'amount' not in data:
                data['amount'] = 1.00  # 自投默认1.00元
        elif target_project and target_project.members.filter(id=voter.id).exists():
            data['vote_type'] = 'project'
        else:
            data['vote_type'] = 'individual'

        return data

    def create(self, validated_data):
        validated_data['voter'] = self.context['request'].user
        return super().create(validated_data)

class ContributionEvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source='evaluator.username', read_only=True)
    evaluated_user_name = serializers.CharField(source='evaluated_user.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = ContributionEvaluation
        fields = ('id', 'evaluator', 'evaluator_name', 'evaluated_user', 'evaluated_user_name', 'project', 'project_name', 'voting_round', 'contribution_score', 'comment', 'created_at')

class ContributionEvaluationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionEvaluation
        fields = ('evaluated_user', 'project', 'voting_round', 'contribution_score', 'comment')

    def create(self, validated_data):
        validated_data['evaluator'] = self.context['request'].user
        return super().create(validated_data)

class SelfEvaluationSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source='investor.username', read_only=True)
    target_name = serializers.SerializerMethodField()
    voting_round_name = serializers.CharField(source='voting_round.name', read_only=True)

    class Meta:
        model = SelfEvaluation
        fields = ('id', 'entity_type', 'entity_id', 'investor', 'investor_name', 'target_name', 'voting_round', 'voting_round_name',
                  'investment_amount', 'previous_valuation', 'new_valuation', 
                  'previous_equity_percentage', 'new_equity_percentage', 'dilution_percentage',
                  'is_approved', 'created_at')

    def get_target_name(self, obj):
        if obj.entity_type == 'user':
            from apps.users.models import User
            try:
                user = User.objects.get(id=obj.entity_id)
                return user.username
            except User.DoesNotExist:
                return '未知用户'
        else:
            from apps.projects.models import Project
            try:
                project = Project.objects.get(id=obj.entity_id)
                return project.name
            except Project.DoesNotExist:
                return '未知项目'

class SelfEvaluationCreateSerializer(serializers.ModelSerializer):
    voting_round = serializers.PrimaryKeyRelatedField(
        queryset=VotingRound.objects.all(),
        required=False
    )
    
    class Meta:
        model = SelfEvaluation
        fields = ('entity_type', 'entity_id', 'voting_round', 'investment_amount', 
                  'previous_valuation', 'new_valuation')

    def validate(self, data):
        # 如果没有传递voting_round，自动使用活跃轮次
        if not data.get('voting_round'):
            active_round = VotingRound.objects.filter(is_active=True).first()
            if not active_round:
                raise serializers.ValidationError("没有找到活跃的投票轮次")
            data['voting_round'] = active_round
        
        # 计算股权变化
        investment_amount = data['investment_amount']
        previous_valuation = data['previous_valuation']
        new_valuation = data['new_valuation']
        
        # 计算稀释比例
        dilution = (investment_amount / new_valuation) * 100
        data['dilution_percentage'] = dilution
        
        # 计算投资前后股权比例
        data['previous_equity_percentage'] = 100.0  # 假设投资前100%股权
        data['new_equity_percentage'] = 100.0 - dilution  # 投资后剩余股权
        
        return data

    def create(self, validated_data):
        validated_data['investor'] = self.context['request'].user
        return super().create(validated_data)

# 评分活动序列化器
class RatingSessionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    selected_members_detail = serializers.SerializerMethodField()
    member_count = serializers.ReadOnlyField()
    rating_count = serializers.ReadOnlyField()

    class Meta:
        model = RatingSession
        fields = ('id', 'project', 'project_name', 'theme', 'description', 'created_by', 'created_by_name',
                  'status', 'selected_members', 'selected_members_detail', 'total_points', 'member_count',
                  'rating_count', 'created_at', 'ended_at')

    def get_selected_members_detail(self, obj):
        return [{'id': member.id, 'username': member.username} for member in obj.selected_members.all()]

class RatingSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingSession
        fields = ('project', 'theme', 'description', 'selected_members', 'total_points')

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

# 评分记录序列化器
class RatingSerializer(serializers.ModelSerializer):
    session_theme = serializers.CharField(source='session.theme', read_only=True)
    rater_name = serializers.CharField(source='rater.username', read_only=True)
    target_name = serializers.CharField(source='target.username', read_only=True)

    class Meta:
        model = Rating
        fields = ('id', 'session', 'session_theme', 'rater', 'rater_name', 'target', 'target_name',
                  'score', 'remark', 'created_at', 'updated_at')

class RatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ('session', 'target', 'score', 'remark')

    def validate(self, data):
        session = data['session']
        target = data['target']
        request = self.context['request']

        # 检查评分活动状态
        if session.status != 'active':
            raise serializers.ValidationError("评分活动已结束，无法提交评分")

        # 检查目标用户是否是评分活动的参与成员
        if not session.selected_members.filter(id=target.id).exists():
            raise serializers.ValidationError("目标用户不是该评分活动的参与成员")

        # 检查评分者是否是评分活动的参与成员
        if not session.selected_members.filter(id=request.user.id).exists():
            raise serializers.ValidationError("您不是该评分活动的参与成员")

        return data

    def create(self, validated_data):
        validated_data['rater'] = self.context['request'].user
        return super().create(validated_data)