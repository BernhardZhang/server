from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class MeritRound(models.Model):
    """功分互评轮次"""
    name = models.CharField(max_length=200, verbose_name='评价轮次名称')
    description = models.TextField(blank=True, verbose_name='评价轮次描述')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    is_active = models.BooleanField(default=False, verbose_name='是否活跃')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '功分互评轮次'
        verbose_name_plural = '功分互评轮次'

    def __str__(self):
        return self.name


class ContributionEvaluation(models.Model):
    """贡献度评价"""
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='merit_evaluations_given', 
        verbose_name='评价人'
    )
    evaluated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='merit_evaluations_received', 
        verbose_name='被评价人'
    )
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        related_name='merit_contribution_evaluations',
        verbose_name='项目'
    )
    merit_round = models.ForeignKey(
        MeritRound, 
        on_delete=models.CASCADE, 
        verbose_name='评价轮次'
    )
    contribution_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], 
        verbose_name='贡献分数'
    )
    comment = models.TextField(blank=True, verbose_name='评价意见')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评价时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = ['evaluator', 'evaluated_user', 'project', 'merit_round']
        verbose_name = '贡献评价'
        verbose_name_plural = '贡献评价'

    def __str__(self):
        return f"{self.evaluator.username} 评价 {self.evaluated_user.username} 在 {self.project.name} 的贡献: {self.contribution_score}"


class MeritCriteria(models.Model):
    """评价标准"""
    name = models.CharField(max_length=100, verbose_name='标准名称')
    description = models.TextField(verbose_name='标准描述')
    weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(0.1), MaxValueValidator(1.0)],
        verbose_name='权重'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '评价标准'
        verbose_name_plural = '评价标准'

    def __str__(self):
        return self.name


class DetailedEvaluation(models.Model):
    """详细评价记录"""
    base_evaluation = models.ForeignKey(
        ContributionEvaluation,
        on_delete=models.CASCADE,
        related_name='detailed_evaluations',
        verbose_name='基础评价'
    )
    criteria = models.ForeignKey(
        MeritCriteria,
        on_delete=models.CASCADE,
        verbose_name='评价标准'
    )
    score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='分数'
    )
    comment = models.TextField(blank=True, verbose_name='详细意见')

    class Meta:
        unique_together = ['base_evaluation', 'criteria']
        verbose_name = '详细评价'
        verbose_name_plural = '详细评价'

    def __str__(self):
        return f"{self.base_evaluation} - {self.criteria.name}: {self.score}"