from django.db import models
from django.conf import settings
from decimal import Decimal

class FinancialReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('individual', '个人财务报表'),
        ('project', '项目财务报表'),
    ]
    
    DATA_SOURCE_CHOICES = [
        ('manual', '手工输入'),
        ('calculated', '系统计算'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, verbose_name='用户')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, verbose_name='项目')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='报表类型')
    data_source = models.CharField(max_length=20, choices=DATA_SOURCE_CHOICES, default='manual', verbose_name='数据来源')
    voting_round = models.ForeignKey('voting.VotingRound', on_delete=models.CASCADE, related_name='finance_reports', verbose_name='投票轮次')
    
    # 资产负债表
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='总资产')
    current_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='流动资产')
    fixed_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='固定资产')
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='总负债')
    equity = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='所有者权益')
    
    # 利润表
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='营业收入')
    costs = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='营业成本')
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='毛利润')
    operating_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='营业费用')
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='净利润')
    
    # 现金流量表
    operating_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='经营活动现金流')
    investing_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='投资活动现金流')
    financing_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='筹资活动现金流')
    net_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='净现金流')
    
    is_authorized = models.BooleanField(default=False, verbose_name='是否授权公开')
    authorized_at = models.DateTimeField(null=True, blank=True, verbose_name='授权时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        unique_together = [
            ['user', 'voting_round'],
            ['project', 'voting_round']
        ]
        verbose_name = '财务报表'
        verbose_name_plural = '财务报表'

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.voting_round.name} 财务报表"
        else:
            return f"{self.project.name} - {self.voting_round.name} 财务报表"

    def save(self, *args, **kwargs):
        # 自动计算相关字段
        self.gross_profit = self.revenue - self.costs
        self.net_profit = self.gross_profit - Decimal(self.operating_expenses)
        self.net_cash_flow = self.operating_cash_flow + Decimal(self.investing_cash_flow) + Decimal(self.financing_cash_flow)
        super().save(*args, **kwargs)

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('vote_payment', '投票支付'),
        ('investment', '投资'),
        ('dividend', '分红'),
        ('refund', '退款'),
        ('deposit', '充值'),
        ('withdrawal', '提现'),
    ]
    
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions_sent', verbose_name='发起人')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions_received', null=True, blank=True, verbose_name='接收人')
    to_project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, verbose_name='接收项目')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='金额')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, verbose_name='交易类型')
    description = models.TextField(blank=True, verbose_name='交易描述')
    related_vote = models.ForeignKey('voting.Vote', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关投票')
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name='交易ID')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '交易记录'
        verbose_name_plural = '交易记录'

    def __str__(self):
        target = self.to_user.username if self.to_user else self.to_project.name
        return f"{self.from_user.username} -> {target}: {self.amount}元 ({self.get_transaction_type_display()})"

class ShareholderEquity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='股东')
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equity_holders', null=True, blank=True, verbose_name='目标用户')
    target_project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, verbose_name='目标项目')
    investment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='投资金额')
    equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='股权比例')
    voting_round = models.ForeignKey('voting.VotingRound', on_delete=models.CASCADE, related_name='share_holdings', verbose_name='投票轮次')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        unique_together = [
            ['user', 'target_user', 'voting_round'],
            ['user', 'target_project', 'voting_round']
        ]
        verbose_name = '股权记录'
        verbose_name_plural = '股权记录'

    def __str__(self):
        target = self.target_user.username if self.target_user else self.target_project.name
        return f"{self.user.username} 持有 {target} {self.equity_percentage}% 股权"