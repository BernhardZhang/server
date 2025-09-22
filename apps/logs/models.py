from django.db import models
from django.conf import settings
import os


class ProjectLog(models.Model):
    """项目日志模型"""
    LOG_TYPE_CHOICES = [
        # 项目相关操作
        ('project_created', '项目创建'),
        ('project_updated', '项目更新'),
        ('project_deleted', '项目删除'),
        ('project_archived', '项目归档'),
        ('project_restored', '项目恢复'),

        # 成员管理操作
        ('member_joined', '成员加入'),
        ('member_left', '成员离开'),
        ('member_role_changed', '成员角色变更'),
        ('member_invited', '邀请成员'),
        ('member_removed', '移除成员'),
        ('member_permission_changed', '成员权限变更'),

        # 文件操作
        ('file_uploaded', '文件上传'),
        ('file_deleted', '文件删除'),
        ('file_downloaded', '文件下载'),
        ('file_shared', '文件分享'),

        # 评论和沟通
        ('comment_added', '评论添加'),
        ('comment_updated', '评论更新'),
        ('comment_deleted', '评论删除'),
        ('message_sent', '发送消息'),

        # 评分和评估
        ('rating_created', '评分创建'),
        ('rating_completed', '评分完成'),
        ('evaluation_started', '评估开始'),
        ('evaluation_completed', '评估完成'),
        ('points_awarded', '积分奖励'),
        ('points_deducted', '积分扣除'),

        # 项目状态和里程碑
        ('milestone_reached', '里程碑达成'),
        ('milestone_created', '里程碑创建'),
        ('milestone_updated', '里程碑更新'),
        ('status_changed', '状态变更'),
        ('progress_updated', '进度更新'),

        # 投票和决策
        ('vote_created', '创建投票'),
        ('vote_participated', '参与投票'),
        ('vote_completed', '投票完成'),
        ('decision_made', '做出决策'),

        # 财务相关
        ('investment_made', '投资操作'),
        ('revenue_recorded', '收益记录'),
        ('expense_recorded', '支出记录'),
        ('valuation_updated', '估值更新'),

        # 系统操作
        ('backup_created', '创建备份'),
        ('settings_changed', '设置变更'),
        ('permission_granted', '授予权限'),
        ('permission_revoked', '撤销权限'),

        # 其他操作
        ('other', '其他操作'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='system_logs', verbose_name='项目')
    log_type = models.CharField(max_length=50, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_system_logs', verbose_name='操作用户')
    title = models.CharField(max_length=200, verbose_name='日志标题')
    description = models.TextField(blank=True, verbose_name='详细描述')

    # 操作详细信息
    action_method = models.CharField(max_length=50, blank=True, verbose_name='操作方法', help_text='如：POST, PUT, DELETE, GET等')
    action_function = models.CharField(max_length=100, blank=True, verbose_name='操作功能', help_text='如：创建任务、更新项目、分配成员等')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')

    # 相关对象信息（可选）
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_system_logs_about',
        verbose_name='相关用户'
    )

    # 变更数据（JSON格式存储变更前后的值）
    changes = models.JSONField(default=dict, blank=True, verbose_name='变更内容')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        verbose_name = '项目日志'
        verbose_name_plural = '项目日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.get_log_type_display()} - {self.user.username}"


class TaskLog(models.Model):
    """任务日志模型"""
    LOG_TYPE_CHOICES = [
        # 任务状态操作
        ('task_created', '任务创建'),
        ('task_updated', '任务更新'),
        ('task_deleted', '任务删除'),
        ('task_completed', '任务完成'),
        ('task_assigned', '任务分配'),
        ('task_reassigned', '任务重新分配'),
        ('task_priority_changed', '任务优先级变更'),
        ('task_deadline_changed', '任务截止日期变更'),
        ('task_progress_updated', '任务进度更新'),
        ('task_status_changed', '任务状态变更'),

        # 文件操作
        ('file_uploaded', '文件上传'),
        ('file_deleted', '文件删除'),
        ('file_downloaded', '文件下载'),
        ('file_shared', '文件分享'),

        # 评论操作
        ('comment_added', '评论添加'),
        ('comment_updated', '评论更新'),
        ('comment_deleted', '评论删除'),

        # 评分操作
        ('evaluation_submitted', '评分提交'),
        ('evaluation_updated', '评分更新'),

        # 其他操作
        ('other', '其他操作'),
    ]

    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, related_name='system_logs', verbose_name='任务')
    log_type = models.CharField(max_length=50, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_system_logs', verbose_name='操作用户')
    title = models.CharField(max_length=200, verbose_name='日志标题')
    description = models.TextField(blank=True, verbose_name='详细描述')

    # 操作详细信息
    action_method = models.CharField(max_length=50, blank=True, verbose_name='操作方法')
    action_function = models.CharField(max_length=100, blank=True, verbose_name='操作功能')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')

    # 相关对象信息
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_system_logs_about',
        verbose_name='相关用户'
    )

    # 变更数据
    changes = models.JSONField(default=dict, blank=True, verbose_name='变更内容')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        verbose_name = '任务日志'
        verbose_name_plural = '任务日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.task.title} - {self.get_log_type_display()} - {self.user.username}"


class TaskUserLog(models.Model):
    """任务用户工作日志"""
    LOG_TYPE_CHOICES = [
        ('work_start', '开始工作'),
        ('work_pause', '暂停工作'),
        ('work_resume', '恢复工作'),
        ('work_complete', '工作完成'),
        ('progress_update', '进度更新'),
        ('issue_reported', '问题报告'),
        ('solution_provided', '解决方案'),
        ('milestone_reached', '里程碑达成'),
        ('note_added', '添加备注'),
        ('other', '其他'),
    ]

    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, related_name='system_user_logs', verbose_name='任务')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_system_user_logs', verbose_name='用户')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')

    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='日志内容')

    # 工作时间记录
    work_duration = models.DurationField(null=True, blank=True, verbose_name='工作时长')
    progress_percentage = models.IntegerField(default=0, verbose_name='进度百分比')

    # 位置信息
    location = models.CharField(max_length=100, blank=True, verbose_name='工作地点')

    # 标签和分类
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    priority = models.CharField(
        max_length=10,
        choices=[('low', '低'), ('medium', '中'), ('high', '高'), ('urgent', '紧急')],
        default='medium',
        verbose_name='优先级'
    )

    # 关联信息
    related_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='related_task_system_user_logs',
        blank=True,
        verbose_name='相关用户'
    )

    # 状态
    is_important = models.BooleanField(default=False, verbose_name='是否重要')
    is_private = models.BooleanField(default=False, verbose_name='是否私有')

    # 时间戳
    logged_at = models.DateTimeField(verbose_name='日志时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '任务用户日志'
        verbose_name_plural = '任务用户日志'
        ordering = ['-logged_at']
        indexes = [
            models.Index(fields=['task', 'user', '-logged_at']),
            models.Index(fields=['user', '-logged_at']),
            models.Index(fields=['log_type', '-logged_at']),
        ]

    def __str__(self):
        return f"{self.task.title} - {self.user.username} - {self.title}"


class TaskUserLogAttachment(models.Model):
    """任务用户日志附件"""
    FILE_TYPE_CHOICES = [
        ('image', '图片'),
        ('document', '文档'),
        ('video', '视频'),
        ('audio', '音频'),
        ('archive', '压缩包'),
        ('other', '其他'),
    ]

    log = models.ForeignKey(TaskUserLog, on_delete=models.CASCADE, related_name='attachments', verbose_name='日志')
    file = models.FileField(upload_to='task_user_log_attachments/%Y/%m/%d/', verbose_name='附件')
    filename = models.CharField(max_length=255, verbose_name='文件名')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other', verbose_name='文件类型')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    description = models.TextField(blank=True, verbose_name='文件描述')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')

    class Meta:
        verbose_name = '任务用户日志附件'
        verbose_name_plural = '任务用户日志附件'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.log.title} - {self.filename}"

    def save(self, *args, **kwargs):
        if self.file:
            # 设置文件大小
            self.file_size = self.file.size
            # 根据文件扩展名自动设置文件类型
            if not self.file_type or self.file_type == 'other':
                self.file_type = self.detect_file_type()
        super().save(*args, **kwargs)

    def detect_file_type(self):
        """根据文件扩展名检测文件类型"""
        if not self.file:
            return 'other'

        name, ext = os.path.splitext(self.filename.lower())

        if ext in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx']:
            return 'document'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
            return 'image'
        elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
            return 'video'
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
            return 'audio'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'archive'
        else:
            return 'other'

    @property
    def file_size_display(self):
        """人性化显示文件大小"""
        if not self.file_size:
            return '未知'

        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"


class SystemLog(models.Model):
    """系统日志模型 - 为将来扩展准备"""
    LOG_LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    LOG_TYPE_CHOICES = [
        ('system', '系统操作'),
        ('auth', '认证相关'),
        ('database', '数据库操作'),
        ('api', 'API调用'),
        ('file', '文件操作'),
        ('email', '邮件发送'),
        ('other', '其他'),
    ]

    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, verbose_name='日志级别')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')
    title = models.CharField(max_length=200, verbose_name='标题')
    message = models.TextField(verbose_name='日志消息')

    # 用户信息（可选）
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='相关用户'
    )

    # 请求信息
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')
    request_path = models.CharField(max_length=500, blank=True, verbose_name='请求路径')
    request_method = models.CharField(max_length=10, blank=True, verbose_name='请求方法')

    # 额外数据
    extra_data = models.JSONField(default=dict, blank=True, verbose_name='额外数据')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '系统日志'
        verbose_name_plural = '系统日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"