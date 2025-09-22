from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone


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


class ProjectMeritCalculation(models.Model):
    """项目功分计算记录"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='merit_calculations',
        verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='计算名称')
    description = models.TextField(blank=True, verbose_name='计算说明')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')

    # 计算配置
    total_project_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name='项目总价值（分）'
    )

    # 时间设置
    calculation_start_date = models.DateTimeField(null=True, blank=True, verbose_name='计算开始时间')
    calculation_end_date = models.DateTimeField(null=True, blank=True, verbose_name='计算结束时间')
    peer_review_deadline = models.DateTimeField(null=True, blank=True, verbose_name='互评截止时间')

    # 创建信息
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_merit_calculations',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '项目功分计算'
        verbose_name_plural = '项目功分计算'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class TaskMeritAssignment(models.Model):
    """任务功分分配"""
    calculation = models.ForeignKey(
        ProjectMeritCalculation,
        on_delete=models.CASCADE,
        related_name='task_assignments',
        verbose_name='功分计算'
    )
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='merit_assignments',
        verbose_name='任务'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_merit_assignments',
        verbose_name='用户'
    )

    # 任务分配权重
    task_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='任务占比（%）'
    )
    role_weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(0.1), MaxValueValidator(3.0)],
        verbose_name='角色权重系数'
    )

    # 时效系数计算
    planned_start_date = models.DateField(null=True, blank=True, verbose_name='计划开始日期')
    planned_end_date = models.DateField(null=True, blank=True, verbose_name='计划完成日期')
    actual_end_date = models.DateField(null=True, blank=True, verbose_name='实际完成日期')
    time_coefficient = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='时效系数'
    )

    # 系统分计算结果
    system_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='系统分'
    )

    # 功分（通过互评计算）
    function_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='功分'
    )

    # 总分
    total_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='总分'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = ['calculation', 'task', 'user']
        verbose_name = '任务功分分配'
        verbose_name_plural = '任务功分分配'
        ordering = ['-total_score']

    def __str__(self):
        return f"{self.user.username} - {self.task.title}: {self.total_score}分"

    def calculate_time_coefficient(self):
        """计算时效系数"""
        if not self.planned_end_date or not self.actual_end_date:
            return Decimal('1.00')

        # 计算提前/延迟天数
        days_diff = (self.actual_end_date - self.planned_end_date).days

        if days_diff <= -7:  # 提前7天以上
            return Decimal('1.30')
        elif days_diff <= -4:  # 提前4-6天
            return Decimal('1.30')
        elif days_diff <= -1:  # 提前1-3天
            return Decimal('1.20')
        elif days_diff == 0:  # 按时完成
            return Decimal('1.00')
        else:
            # 计算超时比例
            planned_duration = (self.planned_end_date - self.planned_start_date).days if self.planned_start_date else 30
            if planned_duration <= 0:
                planned_duration = 30  # 默认30天

            overtime_ratio = days_diff / planned_duration

            if overtime_ratio <= 0.1:  # 超时≤10%
                return Decimal('0.90')
            elif overtime_ratio <= 0.3:  # 10% < 超时≤30%
                return Decimal('0.70')
            else:  # 超时 > 30%
                return Decimal('0.50')

    def calculate_system_score(self):
        """计算系统分：任务占比 × 角色权重 × 时效系数"""
        if self.calculation:
            base_score = self.calculation.total_project_value * (self.task_percentage / 100)
            return base_score * self.role_weight * self.time_coefficient
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        # 自动计算时效系数
        if self.actual_end_date:
            self.time_coefficient = self.calculate_time_coefficient()

        # 自动计算系统分
        self.system_score = self.calculate_system_score()

        # 计算总分
        self.total_score = self.system_score + self.function_score

        super().save(*args, **kwargs)


class PeerReview(models.Model):
    """匿名互评记录"""
    calculation = models.ForeignKey(
        ProjectMeritCalculation,
        on_delete=models.CASCADE,
        related_name='peer_reviews',
        verbose_name='功分计算'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_peer_reviews',
        verbose_name='评价人'
    )
    reviewed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_peer_reviews',
        verbose_name='被评价人'
    )

    # 评分
    score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='评分（0-100分）'
    )

    # 评价维度（可选的详细评分）
    work_quality_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='工作质量评分'
    )
    collaboration_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='团队协作评分'
    )
    efficiency_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='工作效率评分'
    )
    innovation_score = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='创新程度评分'
    )

    # 评价意见
    comment = models.TextField(blank=True, verbose_name='评价意见')

    # 匿名标识
    is_anonymous = models.BooleanField(default=True, verbose_name='是否匿名')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评价时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = ['calculation', 'reviewer', 'reviewed_user']
        verbose_name = '同行互评'
        verbose_name_plural = '同行互评'
        ordering = ['-created_at']

    def __str__(self):
        reviewer_name = "匿名用户" if self.is_anonymous else self.reviewer.username
        return f"{reviewer_name} 评价 {self.reviewed_user.username}: {self.score}分"


class MeritCalculationResult(models.Model):
    """功分计算最终结果"""
    calculation = models.ForeignKey(
        ProjectMeritCalculation,
        on_delete=models.CASCADE,
        related_name='final_results',
        verbose_name='功分计算'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merit_calculation_results',
        verbose_name='用户'
    )

    # 系统分汇总
    total_system_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='系统分总计'
    )

    # 互评统计
    total_peer_reviews_received = models.IntegerField(default=0, verbose_name='收到的互评数量')
    average_peer_review_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='互评平均分'
    )

    # 功分计算
    individual_points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='个人获得积分'
    )
    total_team_points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='全队总积分'
    )
    function_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='功分得分'
    )

    # 综合得分
    final_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='最终得分'
    )

    # 排名
    rank = models.IntegerField(null=True, blank=True, verbose_name='排名')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='计算时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = ['calculation', 'user']
        verbose_name = '功分计算结果'
        verbose_name_plural = '功分计算结果'
        ordering = ['-final_score']

    def __str__(self):
        return f"{self.user.username} - {self.calculation.name}: {self.final_score}分 (第{self.rank}名)"

    def calculate_function_score(self):
        """计算功分得分：个人获得积分 ÷ 全队总积分 × 30分"""
        if self.total_team_points > 0:
            return (self.individual_points / self.total_team_points) * Decimal('30.00')
        return Decimal('0.00')

    def calculate_final_score(self):
        """计算最终得分：系统分 + 功分得分"""
        return self.total_system_score + self.function_score

    def save(self, *args, **kwargs):
        # 自动计算功分和最终得分
        self.function_score = self.calculate_function_score()
        self.final_score = self.calculate_final_score()
        super().save(*args, **kwargs)


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