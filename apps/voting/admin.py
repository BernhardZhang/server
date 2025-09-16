from django.contrib import admin
from .models import VotingRound, Vote, ContributionEvaluation, SelfEvaluation, RatingSession, Rating

@admin.register(VotingRound)
class VotingRoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'is_active', 'is_self_evaluation_open', 'max_self_investment')
    list_filter = ('is_active', 'is_self_evaluation_open', 'start_time')
    search_fields = ('name', 'description')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'get_target', 'amount', 'vote_type', 'voting_round', 'is_paid', 'created_at')
    list_filter = ('vote_type', 'is_paid', 'voting_round', 'created_at')
    search_fields = ('voter__username', 'target_user__username', 'target_project__name')

    def get_target(self, obj):
        if obj.target_user:
            return f"用户: {obj.target_user.username}"
        elif obj.target_project:
            return f"项目: {obj.target_project.name}"
        return "无目标"
    get_target.short_description = '投票目标'

@admin.register(ContributionEvaluation)
class ContributionEvaluationAdmin(admin.ModelAdmin):
    list_display = ('evaluator', 'evaluated_user', 'project', 'contribution_score', 'voting_round', 'created_at')
    list_filter = ('contribution_score', 'voting_round', 'project', 'created_at')
    search_fields = ('evaluator__username', 'evaluated_user__username', 'project__name')

@admin.register(SelfEvaluation)
class SelfEvaluationAdmin(admin.ModelAdmin):
    list_display = ('investor', 'get_entity', 'investment_amount', 'new_valuation', 'dilution_percentage', 'is_approved', 'created_at')
    list_filter = ('entity_type', 'is_approved', 'voting_round', 'created_at')
    search_fields = ('investor__username',)

    def get_entity(self, obj):
        if obj.entity_type == 'user':
            from apps.users.models import User
            try:
                user = User.objects.get(id=obj.entity_id)
                return f"用户: {user.username}"
            except User.DoesNotExist:
                return "未知用户"
        else:
            from apps.projects.models import Project
            try:
                project = Project.objects.get(id=obj.entity_id)
                return f"项目: {project.name}"
            except Project.DoesNotExist:
                return "未知项目"
    get_entity.short_description = '评估对象'

@admin.register(RatingSession)
class RatingSessionAdmin(admin.ModelAdmin):
    list_display = ('project', 'theme', 'created_by', 'status', 'member_count', 'rating_count', 'total_points', 'created_at')
    list_filter = ('status', 'created_at', 'project')
    search_fields = ('theme', 'description', 'project__name', 'created_by__username')
    filter_horizontal = ('selected_members',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('session', 'rater', 'target', 'score', 'created_at')
    list_filter = ('score', 'created_at', 'session__project')
    search_fields = ('rater__username', 'target__username', 'session__theme', 'remark')