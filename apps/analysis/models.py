from django.db import models
from django.conf import settings

class AnalysisReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('user_performance', '用户绩效分析'),
        ('project_progress', '项目进度分析'),
        ('voting_statistics', '投票统计分析'),
        ('financial_overview', '财务概览分析'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='报告标题')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='报告类型')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='创建人')
    data = models.JSONField(verbose_name='分析数据')
    summary = models.TextField(verbose_name='分析摘要')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '分析报告'
        verbose_name_plural = '分析报告'

    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"

class DataMetric(models.Model):
    name = models.CharField(max_length=100, verbose_name='指标名称')
    description = models.TextField(blank=True, verbose_name='指标描述')
    metric_type = models.CharField(max_length=50, verbose_name='指标类型')
    value = models.JSONField(verbose_name='指标值')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')

    class Meta:
        verbose_name = '数据指标'
        verbose_name_plural = '数据指标'

    def __str__(self):
        return f"{self.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"