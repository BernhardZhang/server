from django.db import models
from django.conf import settings

class DashboardWidget(models.Model):
    WIDGET_TYPE_CHOICES = [
        ('chart', '图表'),
        ('metric', '指标卡'),
        ('table', '表格'),
        ('list', '列表'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='组件名称')
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES, verbose_name='组件类型')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    config = models.JSONField(verbose_name='组件配置')
    position_x = models.IntegerField(default=0, verbose_name='X坐标')
    position_y = models.IntegerField(default=0, verbose_name='Y坐标')
    width = models.IntegerField(default=4, verbose_name='宽度')
    height = models.IntegerField(default=3, verbose_name='高度')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '仪表板组件'
        verbose_name_plural = '仪表板组件'

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    default_view = models.CharField(max_length=50, default='overview', verbose_name='默认视图')
    theme = models.CharField(max_length=20, default='light', verbose_name='主题')
    language = models.CharField(max_length=10, default='zh-cn', verbose_name='语言')
    notifications_enabled = models.BooleanField(default=True, verbose_name='启用通知')
    auto_refresh_interval = models.IntegerField(default=30, verbose_name='自动刷新间隔（秒）')

    class Meta:
        verbose_name = '用户偏好设置'
        verbose_name_plural = '用户偏好设置'

    def __str__(self):
        return f"{self.user.username} 的偏好设置"