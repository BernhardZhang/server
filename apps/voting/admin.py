from django.contrib import admin
from .models import VotingRound, Vote, ContributionEvaluation

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