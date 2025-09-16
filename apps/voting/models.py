from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class VotingRound(models.Model):
    name = models.CharField(max_length=200, verbose_name='投票轮次名称')
    description = models.TextField(blank=True, verbose_name='投票轮次描述')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    is_active = models.BooleanField(default=False, verbose_name='是否活跃')
    is_self_evaluation_open = models.BooleanField(default=False, verbose_name='是否开放自评')
    max_self_investment = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, verbose_name='最大自投金额')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '投票轮次'
        verbose_name_plural = '投票轮次'

    def __str__(self):
        return self.name

class Vote(models.Model):
    VOTE_TYPE_CHOICES = [
        ('individual', '个人投票'),
        ('project', '项目投票'),
        ('self', '自投'),
    ]

    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes_cast', verbose_name='投票人')
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes_received', null=True, blank=True, verbose_name='目标用户')
    target_project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, verbose_name='目标项目')
    voting_round = models.ForeignKey(VotingRound, on_delete=models.CASCADE, related_name='votes', null=True, blank=True, verbose_name='投票轮次')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('1.00'))], verbose_name='投票金额')
    vote_type = models.CharField(max_length=20, choices=VOTE_TYPE_CHOICES, verbose_name='投票类型')
    is_paid = models.BooleanField(default=False, verbose_name='是否已支付')
    payment_transaction_id = models.CharField(max_length=100, blank=True, verbose_name='支付交易ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='投票时间')

    class Meta:
        unique_together = [
            ['voter', 'target_user'],
            ['voter', 'target_project']
        ]
        verbose_name = '投票'
        verbose_name_plural = '投票'

    def __str__(self):
        target = self.target_user.username if self.target_user else self.target_project.name
        return f"{self.voter.username} -> {target}: {self.amount}元"

# 新增：评分活动模型，迁移自projects应用
class RatingSession(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已结束'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='voting_rating_sessions', verbose_name='项目')
    theme = models.CharField(max_length=200, verbose_name='评分主题')
    description = models.TextField(blank=True, verbose_name='评分说明')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='创建者')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    selected_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='voting_rating_sessions',
        verbose_name='参与成员'
    )
    total_points = models.IntegerField(default=100, verbose_name='总分数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')

    class Meta:
        verbose_name = '评分活动'
        verbose_name_plural = '评分活动'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.theme}"

    @property
    def member_count(self):
        return self.selected_members.count()

    @property
    def rating_count(self):
        return self.rating_records.count()

class Rating(models.Model):
    session = models.ForeignKey(RatingSession, on_delete=models.CASCADE, related_name='rating_records', verbose_name='评分活动')
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voting_given_ratings',
        verbose_name='评分者'
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voting_received_ratings',
        verbose_name='被评分者'
    )
    score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='评分'
    )
    remark = models.TextField(blank=True, verbose_name='评分备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = ['session', 'rater', 'target']
        verbose_name = '评分记录'
        verbose_name_plural = '评分记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rater.username} 给 {self.target.username} 评分: {self.score}"

class ContributionEvaluation(models.Model):
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voting_evaluations_given', verbose_name='评价人')
    evaluated_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voting_evaluations_received', verbose_name='被评价人')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='voting_contribution_evaluations', verbose_name='项目')
    voting_round = models.ForeignKey(VotingRound, on_delete=models.CASCADE, related_name='contribution_evaluations', verbose_name='投票轮次')
    contribution_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='贡献分数')
    comment = models.TextField(blank=True, verbose_name='评价意见')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评价时间')

    class Meta:
        unique_together = ['evaluator', 'evaluated_user', 'project', 'voting_round']
        verbose_name = '贡献评价'
        verbose_name_plural = '贡献评价'

    def __str__(self):
        return f"{self.evaluator.username} 评价 {self.evaluated_user.username} 在 {self.project.name} 的贡献: {self.contribution_score}"

class SelfEvaluation(models.Model):
    """自评增资记录"""
    ENTITY_TYPE_CHOICES = [
        ('user', '个人'),
        ('project', '项目'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES, verbose_name='实体类型')
    entity_id = models.PositiveIntegerField(verbose_name='实体ID')
    investor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='self_evaluations', verbose_name='投资人')
    voting_round = models.ForeignKey(VotingRound, on_delete=models.CASCADE, related_name='self_evaluations', verbose_name='投票轮次')

    # 投资信息
    investment_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('10.00'))], verbose_name='投资金额')
    previous_valuation = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='投资前估值')
    new_valuation = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='投资后估值')

    # 股份变化
    previous_equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='投资前股份比例')
    new_equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='投资后股份比例')
    dilution_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='稀释比例')

    is_approved = models.BooleanField(default=True, verbose_name='是否已批准')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '自评增资'
        verbose_name_plural = '自评增资'
        unique_together = ['entity_type', 'entity_id', 'voting_round', 'investor']

    def __str__(self):
        return f"{self.investor.username} 对 {self.get_entity_type_display()} 自评增资 ¥{self.investment_amount}"

class FinancialReport(models.Model):
    """财务报表"""
    ENTITY_TYPE_CHOICES = [
        ('user', '个人'),
        ('project', '项目'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES, verbose_name='实体类型')
    entity_id = models.PositiveIntegerField(verbose_name='实体ID')
    voting_round = models.ForeignKey(VotingRound, on_delete=models.CASCADE, related_name='voting_reports', verbose_name='投票轮次')

    # 资产负债表
    total_assets = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='总资产')
    current_assets = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='流动资产')
    fixed_assets = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='固定资产')
    total_liabilities = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='总负债')
    equity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='所有者权益')

    # 利润表
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='营业收入')
    costs = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='营业成本')
    gross_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='毛利润')
    operating_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='营业费用')
    net_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='净利润')

    # 现金流量表
    operating_cash_flow = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='经营现金流')
    investing_cash_flow = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='投资现金流')
    financing_cash_flow = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='筹资现金流')
    net_cash_flow = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='净现金流')

    # 授权设置
    is_authorized = models.BooleanField(default=False, verbose_name='是否授权公开')
    authorized_at = models.DateTimeField(null=True, blank=True, verbose_name='授权时间')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '财务报表'
        verbose_name_plural = '财务报表'
        unique_together = ['entity_type', 'entity_id', 'voting_round']

    def __str__(self):
        return f"{self.get_entity_type_display()} 财务报表 - 轮次{self.voting_round.name}"

class EquityCalculation(models.Model):
    """股份计算记录"""
    ENTITY_TYPE_CHOICES = [
        ('user', '个人'),
        ('project', '项目'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES, verbose_name='实体类型')
    entity_id = models.PositiveIntegerField(verbose_name='实体ID')
    voting_round = models.ForeignKey(VotingRound, on_delete=models.CASCADE, related_name='equity_calculations', verbose_name='投票轮次')

    # 投资股份计算
    total_investment_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='收到的总投资')
    total_investment_made = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='对外投资总额')
    investment_equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='投资股份比例')

    # 贡献股份计算
    total_contribution_score = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name='总贡献评分')
    contribution_equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='贡献股份比例')

    # 最终股份
    final_equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='最终股份比例')

    # 计算详情
    calculation_details = models.JSONField(default=dict, verbose_name='计算详情')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '股份计算'
        verbose_name_plural = '股份计算'
        unique_together = ['entity_type', 'entity_id', 'voting_round']

    def __str__(self):
        return f"{self.get_entity_type_display()} 股份计算 - 轮次{self.voting_round.name}"