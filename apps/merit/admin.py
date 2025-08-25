from django.contrib import admin
from .models import MeritRound, ContributionEvaluation, MeritCriteria, DetailedEvaluation


@admin.register(MeritRound)
class MeritRoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'start_time', 'end_time', 'created_at')
    list_filter = ('is_active', 'start_time', 'end_time')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(MeritCriteria)
class MeritCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'weight', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)


class DetailedEvaluationInline(admin.TabularInline):
    model = DetailedEvaluation
    extra = 0


@admin.register(ContributionEvaluation)
class ContributionEvaluationAdmin(admin.ModelAdmin):
    list_display = ('evaluator', 'evaluated_user', 'project', 'merit_round', 'contribution_score', 'created_at')
    list_filter = ('merit_round', 'project', 'contribution_score', 'created_at')
    search_fields = ('evaluator__username', 'evaluated_user__username', 'project__name', 'comment')
    ordering = ('-created_at',)
    inlines = [DetailedEvaluationInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'evaluator', 'evaluated_user', 'project', 'merit_round'
        )


@admin.register(DetailedEvaluation)
class DetailedEvaluationAdmin(admin.ModelAdmin):
    list_display = ('base_evaluation', 'criteria', 'score')
    list_filter = ('criteria', 'score')
    search_fields = ('base_evaluation__evaluator__username', 'base_evaluation__evaluated_user__username', 'criteria__name')
    ordering = ('-base_evaluation__created_at',)