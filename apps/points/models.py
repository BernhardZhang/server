from django.db import models
from django.conf import settings

class PointsRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('earned', '获得积分'),
        ('spent', '消费积分'),
        ('bonus', '奖励积分'),
        ('penalty', '扣除积分'),
        ('transfer_in', '转入积分'),
        ('transfer_out', '转出积分'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_records', verbose_name='用户')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES, verbose_name='记录类型')
    amount = models.IntegerField(verbose_name='积分数量')
    description = models.TextField(verbose_name='描述')
    related_vote = models.ForeignKey('voting.Vote', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关投票')
    related_project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关项目')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '积分记录'
        verbose_name_plural = '积分记录'

    def __str__(self):
        return f"{self.user.username} {self.get_record_type_display()} {self.amount}积分"

class PointsTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_sent', verbose_name='发送人')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_received', verbose_name='接收人')
    amount = models.IntegerField(verbose_name='积分数量')
    message = models.TextField(blank=True, verbose_name='转账留言')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name='交易ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        verbose_name = '积分转账'
        verbose_name_plural = '积分转账'

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username}: {self.amount}积分"

class PointsReward(models.Model):
    name = models.CharField(max_length=100, verbose_name='奖励名称')
    description = models.TextField(verbose_name='奖励描述')
    points_required = models.IntegerField(verbose_name='所需积分')
    reward_type = models.CharField(max_length=50, verbose_name='奖励类型')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    stock = models.IntegerField(default=0, verbose_name='库存数量')
    image = models.ImageField(upload_to='rewards/', null=True, blank=True, verbose_name='奖励图片')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '积分奖励'
        verbose_name_plural = '积分奖励'

    def __str__(self):
        return f"{self.name} - {self.points_required}积分"

class PointsRedemption(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('approved', '已批准'),
        ('delivered', '已发放'),
        ('rejected', '已拒绝'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    reward = models.ForeignKey(PointsReward, on_delete=models.CASCADE, verbose_name='奖励')
    points_spent = models.IntegerField(verbose_name='消费积分')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    delivery_info = models.JSONField(blank=True, null=True, verbose_name='配送信息')
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='兑换时间')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        verbose_name = '积分兑换'
        verbose_name_plural = '积分兑换'

    def __str__(self):
        return f"{self.user.username} 兑换 {self.reward.name}"