from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class RatingSession(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已结束'),
    ]
    
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='rating_sessions', verbose_name='项目')
    theme = models.CharField(max_length=200, verbose_name='评分主题')
    description = models.TextField(blank=True, verbose_name='评分说明')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='创建者')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    selected_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='rating_sessions', 
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
        return self.ratings.count()

class Rating(models.Model):
    session = models.ForeignKey(RatingSession, on_delete=models.CASCADE, related_name='ratings', verbose_name='评分活动')
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='given_ratings',
        verbose_name='评分者'
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_ratings',
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