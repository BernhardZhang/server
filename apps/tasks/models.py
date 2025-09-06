from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone
import os

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='任务标题')
    description = models.TextField(blank=True, verbose_name='任务描述')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks_created', verbose_name='创建人')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks_assigned', null=True, blank=True, verbose_name='负责人')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, verbose_name='关联项目')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    
    # 任务大厅相关
    is_available_for_claim = models.BooleanField(default=False, verbose_name='是否可被领取')
    allow_claim_without_login = models.BooleanField(default=False, verbose_name='允许未登录领取')
    is_public = models.BooleanField(default=False, verbose_name='是否公开任务')
    
    # 时间相关
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='截止日期')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='完成日期')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    # 进度和工作量
    progress = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='完成进度'
    )
    estimated_hours = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='预估工时'
    )
    actual_hours = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='实际工时'
    )
    
    # 评分系统字段
    system_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='系统分'
    )
    function_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='功分'
    )
    time_coefficient = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='时效系数'
    )
    weight_coefficient = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.1')), MaxValueValidator(Decimal('1.0'))],
        verbose_name='项目权重系数'
    )
    
    # 标签和分类
    tags = models.TextField(blank=True, help_text='标签，用逗号分隔', verbose_name='任务标签')
    category = models.CharField(max_length=50, blank=True, verbose_name='任务分类')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    @property
    def tag_list(self):
        """返回标签列表"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def is_overdue(self):
        """检查任务是否过期"""
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.due_date
        return False
    
    def save(self, *args, **kwargs):
        # 检查是否是更新操作
        is_update = self.pk is not None
        old_task = None
        
        if is_update:
            # 获取旧的任务数据用于日志记录
            try:
                old_task = Task.objects.get(pk=self.pk)
            except Task.DoesNotExist:
                old_task = None
        
        # 如果任务状态变为完成，自动设置完成时间
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            self.progress = 100
            # 计算时效系数
            self.time_coefficient = self.calculate_time_coefficient()
            # 计算系统分
            self.system_score = self.calculate_system_score()
        # 如果状态从完成变为其他状态，清除完成时间
        elif self.status != 'completed' and self.completed_at:
            self.completed_at = None
            self.time_coefficient = Decimal('1.00')
            self.system_score = Decimal('0.00')
        
        super().save(*args, **kwargs)
        
        # 保存后记录日志（需要在视图中调用）
        # 这里不直接记录日志，因为需要request对象和user信息
    
    def calculate_time_coefficient(self):
        """计算时效系数"""
        if not self.due_date or not self.completed_at:
            return Decimal('1.00')
        
        # 计算完成时间与截止时间的差值（天数）
        completed_date = self.completed_at.date()
        due_date = self.due_date.date()
        days_diff = (completed_date - due_date).days
        
        if days_diff < -6:  # 提前7天以上
            return Decimal('1.30')
        elif days_diff < -3:  # 提前4-6天
            return Decimal('1.25')
        elif days_diff < 0:   # 提前1-3天
            return Decimal('1.20')
        elif days_diff == 0:  # 按时完成
            return Decimal('1.00')
        elif days_diff <= 1:  # 超时1天
            return Decimal('0.90')
        elif days_diff <= 3:  # 超时2-3天
            return Decimal('0.70')
        elif days_diff <= 7:  # 超时4-7天
            return Decimal('0.50')
        else:  # 超时7天以上
            return Decimal('0.30')
    
    def calculate_system_score(self):
        """计算系统分：基础分数 × 时效系数"""
        base_score = Decimal('100.00')  # 基础100分
        return base_score * self.time_coefficient

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='任务')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments', verbose_name='作者')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '任务评论'
        verbose_name_plural = '任务评论'

    def __str__(self):
        return f"{self.task.title} - {self.author.username}"

class TaskAttachment(models.Model):
    """任务附件"""
    FILE_TYPE_CHOICES = [
        ('document', '文档'),
        ('image', '图片'),
        ('video', '视频'),
        ('audio', '音频'),
        ('archive', '压缩包'),
        ('other', '其他'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', verbose_name='任务')
    file = models.FileField(upload_to='task_attachments/%Y/%m/%d/', verbose_name='附件')
    filename = models.CharField(max_length=255, verbose_name='文件名')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other', verbose_name='文件类型')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_attachments', verbose_name='上传人')
    description = models.TextField(blank=True, verbose_name='文件描述')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')

    class Meta:
        verbose_name = '任务附件'
        verbose_name_plural = '任务附件'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.task.title} - {self.filename}"
    
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

class TaskEvaluation(models.Model):
    """任务评估评分"""
    SCORE_TYPE_CHOICES = [
        ('function', '功分评估'),
        ('system', '系统分调整'),
    ]
    
    EVALUATION_MODE_CHOICES = [
        ('peer', '同行评分'),
        ('self', '自我评分'),
        ('leader', '领导评分'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='evaluations', verbose_name='任务')
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='task_evaluations_given',
        verbose_name='评分者'
    )
    evaluated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='task_evaluations_received',
        verbose_name='被评分者'
    )
    
    score_type = models.CharField(max_length=20, choices=SCORE_TYPE_CHOICES, default='function', verbose_name='评分类型')
    evaluation_mode = models.CharField(max_length=20, choices=EVALUATION_MODE_CHOICES, default='peer', verbose_name='评估模式')
    
    # 评分结果
    total_score = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='总评分'
    )
    criteria_scores = models.JSONField(default=dict, verbose_name='各维度评分')
    
    # 评分说明
    comment = models.TextField(verbose_name='评分理由')
    improvement_suggestions = models.TextField(blank=True, verbose_name='改进建议')
    
    # 权重
    work_weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='工作量权重'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        unique_together = ['task', 'evaluator', 'evaluated_user']
        verbose_name = '任务评估'
        verbose_name_plural = '任务评估'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.evaluator.username} 评估 {self.evaluated_user.username} - {self.task.title}: {self.total_score}分"

class TaskEvaluationSession(models.Model):
    """任务评估会话"""
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='评估会话名称')
    description = models.TextField(blank=True, verbose_name='评估说明')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, verbose_name='关联项目')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='evaluation_sessions_created',
        verbose_name='创建者'
    )
    
    # 评估对象
    selected_tasks = models.ManyToManyField(Task, verbose_name='待评估任务')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='evaluation_sessions_participated',
        verbose_name='参与者'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    
    # 评估配置
    criteria_config = models.JSONField(
        default=dict,
        verbose_name='评分标准配置'
    )
    
    # 时间设置
    start_time = models.DateTimeField(default=timezone.now, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='评分截止时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '任务评估会话'
        verbose_name_plural = '任务评估会话'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # 如果是新建且没有设置评分标准配置，则设置默认值
        if not self.pk and not self.criteria_config:
            self.criteria_config = {
                '任务质量': {'weight': 0.3, 'max_score': 100},
                '完成效率': {'weight': 0.25, 'max_score': 100},
                '团队协作': {'weight': 0.25, 'max_score': 100},
                '创新程度': {'weight': 0.2, 'max_score': 100}
            }
        super().save(*args, **kwargs)
    
    @property
    def completion_percentage(self):
        """计算评估完成度"""
        if not self.participants.exists():
            return 0
        
        total_required_evaluations = 0
        completed_evaluations = 0
        
        for task in self.selected_tasks.all():
            for participant in self.participants.all():
                # 每个参与者需要评估除自己外的其他人在该任务上的表现
                if task.assignee and task.assignee != participant:
                    total_required_evaluations += 1
                    if TaskEvaluation.objects.filter(
                        task=task,
                        evaluator=participant,
                        evaluated_user=task.assignee
                    ).exists():
                        completed_evaluations += 1
        
        if total_required_evaluations == 0:
            return 100
        
        return int((completed_evaluations / total_required_evaluations) * 100)
    
    def can_complete(self):
        """检查是否可以完成评估"""
        return self.completion_percentage >= 80  # 至少80%的评估完成才能结束
    
    def complete_session(self):
        """完成评估会话并计算最终功分"""
        if not self.can_complete():
            raise ValueError("评估完成度不足，无法完成会话")
        
        self.status = 'completed'
        self.end_time = timezone.now()
        self.save()
        
        # 计算每个任务的最终功分
        self.calculate_final_scores()
    
    def calculate_final_scores(self):
        """计算最终功分"""
        for task in self.selected_tasks.all():
            if not task.assignee:
                continue
            
            # 获取该任务的所有评估
            evaluations = TaskEvaluation.objects.filter(
                task=task,
                evaluated_user=task.assignee
            )
            
            if not evaluations.exists():
                continue
            
            # 计算加权平均分
            total_weighted_score = Decimal('0.00')
            total_weights = Decimal('0.00')
            
            for evaluation in evaluations:
                weight = evaluation.work_weight
                score = evaluation.total_score
                total_weighted_score += score * weight
                total_weights += weight
            
            if total_weights > 0:
                # 计算最终功分
                final_function_score = total_weighted_score / total_weights
                task.function_score = final_function_score
                task.save()
    
    def get_evaluation_summary(self):
        """获取评估摘要统计"""
        summary = {
            'total_tasks': self.selected_tasks.count(),
            'total_participants': self.participants.count(),
            'completion_percentage': self.completion_percentage,
            'average_scores': {},
            'top_performers': [],
        }
        
        # 计算平均分统计
        all_evaluations = TaskEvaluation.objects.filter(
            task__in=self.selected_tasks.all()
        )
        
        if all_evaluations.exists():
            avg_score = all_evaluations.aggregate(
                avg=models.Avg('total_score')
            )['avg']
            summary['average_scores']['overall'] = float(avg_score or 0)
        
        return summary


class TaskLog(models.Model):
    """任务操作日志"""
    ACTION_CHOICES = [
        ('created', '创建任务'),
        ('assigned', '分配任务'),
        ('status_changed', '状态变更'),
        ('priority_changed', '优先级变更'),
        ('updated', '更新任务'),
        ('progress_updated', '进度更新'),
        ('deadline_changed', '截止日期变更'),
        ('comment_added', '添加评论'),
        ('attachment_uploaded', '上传附件'),
        ('attachment_deleted', '删除附件'),
        ('evaluation_added', '添加评估'),
        ('completed', '任务完成'),
        ('cancelled', '取消任务'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs', verbose_name='任务')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_logs', verbose_name='操作人')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='操作类型')
    description = models.TextField(verbose_name='操作描述')
    old_value = models.JSONField(blank=True, null=True, verbose_name='原值')
    new_value = models.JSONField(blank=True, null=True, verbose_name='新值')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        verbose_name = '任务日志'
        verbose_name_plural = '任务日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} {self.get_action_display()} - {self.task.title}"
    
    @classmethod
    def log_action(cls, task, user, action, description, old_value=None, new_value=None, request=None):
        """记录任务操作日志"""
        ip_address = None
        user_agent = ''
        
        if request:
            # 获取客户端IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # 获取用户代理
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # 限制长度
        
        return cls.objects.create(
            task=task,
            user=user,
            action=action,
            description=description,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_change_summary(self):
        """获取变更摘要"""
        if not self.old_value and not self.new_value:
            return self.description
        
        changes = []
        if self.action == 'status_changed':
            old_status = self.old_value.get('status') if self.old_value else None
            new_status = self.new_value.get('status') if self.new_value else None
            if old_status and new_status:
                changes.append(f"状态从 '{old_status}' 变更为 '{new_status}'")
        elif self.action == 'priority_changed':
            old_priority = self.old_value.get('priority') if self.old_value else None
            new_priority = self.new_value.get('priority') if self.new_value else None
            if old_priority and new_priority:
                changes.append(f"优先级从 '{old_priority}' 变更为 '{new_priority}'")
        elif self.action == 'progress_updated':
            old_progress = self.old_value.get('progress') if self.old_value else None
            new_progress = self.new_value.get('progress') if self.new_value else None
            if old_progress is not None and new_progress is not None:
                changes.append(f"进度从 {old_progress}% 更新为 {new_progress}%")
        
        return '; '.join(changes) if changes else self.description


class TaskUserLog(models.Model):
    """用户任务日志 - 用户手动记录的工作日志"""
    LOG_TYPE_CHOICES = [
        ('progress', '进度更新'),
        ('bug', '问题反馈'),
        ('solution', '解决方案'),
        ('note', '工作笔记'),
        ('milestone', '里程碑'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='user_logs', verbose_name='任务')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_user_logs', verbose_name='记录人')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default='note', verbose_name='日志类型')
    title = models.CharField(max_length=200, verbose_name='日志标题')
    content = models.TextField(verbose_name='日志内容')
    progress = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='更新进度'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户任务日志'
        verbose_name_plural = '用户任务日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class TaskUserLogAttachment(models.Model):
    """用户任务日志附件"""
    log = models.ForeignKey(TaskUserLog, on_delete=models.CASCADE, related_name='attachments', verbose_name='日志')
    file = models.FileField(upload_to='task_log_attachments/%Y/%m/%d/', verbose_name='附件')
    filename = models.CharField(max_length=255, verbose_name='文件名')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')

    class Meta:
        verbose_name = '用户任务日志附件'
        verbose_name_plural = '用户任务日志附件'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.log.title} - {self.filename}"


class TaskTeamMeritCalculation(models.Model):
    """任务团队功分计算记录"""
    CALCULATION_METHOD_CHOICES = [
        ('single', '单人参与'),
        ('duo', '双人协作'),
        ('small_group', '小组协作'),
        ('large_group', '大组协作'),
    ]
    
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='merit_calculation', verbose_name='任务')
    calculation_method = models.CharField(max_length=20, choices=CALCULATION_METHOD_CHOICES, verbose_name='计算方法')
    participant_count = models.IntegerField(verbose_name='参与人数')
    total_contribution = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总贡献值')
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name='计算时间')
    is_finalized = models.BooleanField(default=False, verbose_name='是否已确定')
    
    # 计算结果摘要
    calculation_summary = models.JSONField(default=dict, verbose_name='计算摘要')
    
    class Meta:
        verbose_name = '任务团队功分计算'
        verbose_name_plural = '任务团队功分计算'
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"{self.task.title} - {self.get_calculation_method_display()}"
    
    def get_participant_contributions(self):
        """获取参与者贡献值"""
        return {
            result.participant.id: float(result.contribution_value)
            for result in self.participant_results.all()
        }
    
    def get_participant_merit_points(self):
        """获取参与者功分"""
        return {
            result.participant.id: float(result.merit_points)
            for result in self.participant_results.all()
        }
    
    def calculate_merit_points(self):
        """计算功分并保存结果"""
        from utils.merit_calculation import calculate_team_merit_distribution
        
        # 获取所有参与者的贡献值
        contributions = self.get_participant_contributions()
        
        if not contributions:
            return
        
        # 计算功分
        merit_points = calculate_team_merit_distribution(contributions)
        
        # 更新参与者结果
        for user_id, merit_point in merit_points.items():
            result, created = TaskTeamMeritResult.objects.get_or_create(
                calculation=self,
                participant_id=user_id,
                defaults={'merit_points': Decimal(str(merit_point))}
            )
            if not created:
                result.merit_points = Decimal(str(merit_point))
                result.save()
        
        # 更新计算方法
        n = len(contributions)
        if n == 1:
            self.calculation_method = 'single'
        elif n == 2:
            self.calculation_method = 'duo'
        elif 3 <= n <= 10:
            self.calculation_method = 'small_group'
        else:
            self.calculation_method = 'large_group'
        
        self.participant_count = n
        self.total_contribution = sum(Decimal(str(v)) for v in contributions.values())
        
        # 保存计算摘要
        from utils.merit_calculation import get_merit_calculation_info
        self.calculation_summary = get_merit_calculation_info(n)
        
        self.save()
    
    def finalize_calculation(self):
        """确定功分计算结果"""
        if self.is_finalized:
            return
        
        # 将功分更新到任务中
        total_merit = Decimal('0.00')
        for result in self.participant_results.all():
            total_merit += result.merit_points
        
        # 如果任务负责人是主要参与者，更新任务的功分
        if self.task.assignee:
            assignee_result = self.participant_results.filter(
                participant=self.task.assignee
            ).first()
            if assignee_result:
                self.task.function_score = assignee_result.merit_points
                self.task.save()
        
        self.is_finalized = True
        self.save()


class TaskTeamMeritResult(models.Model):
    """任务团队功分计算结果"""
    calculation = models.ForeignKey(
        TaskTeamMeritCalculation, 
        on_delete=models.CASCADE, 
        related_name='participant_results',
        verbose_name='计算记录'
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merit_results',
        verbose_name='参与者'
    )
    contribution_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='贡献值'
    )
    merit_points = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='功分'
    )
    weight_factor = models.DecimalField(
        max_digits=6, 
        decimal_places=4, 
        null=True, 
        blank=True,
        verbose_name='权重因子'
    )
    adjustment_factor = models.DecimalField(
        max_digits=6, 
        decimal_places=4, 
        null=True, 
        blank=True,
        verbose_name='调整因子'
    )
    
    class Meta:
        unique_together = ['calculation', 'participant']
        verbose_name = '团队功分计算结果'
        verbose_name_plural = '团队功分计算结果'
        ordering = ['-merit_points']
    
    def __str__(self):
        return f"{self.participant.username} - {self.merit_points}分"
    
    @property
    def merit_percentage(self):
        """功分占比"""
        total_merit = self.calculation.participant_results.aggregate(
            total=models.Sum('merit_points')
        )['total'] or Decimal('0.00')
        
        if total_merit > 0:
            return float((self.merit_points / total_merit) * 100)
        return 0.0


class TaskContributionRecord(models.Model):
    """任务贡献记录"""
    CONTRIBUTION_TYPE_CHOICES = [
        ('work_quality', '工作质量'),
        ('work_efficiency', '工作效率'),
        ('team_collaboration', '团队协作'),
        ('innovation', '创新程度'),
        ('problem_solving', '问题解决'),
        ('communication', '沟通交流'),
        ('leadership', '领导能力'),
        ('technical_skill', '技术能力'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='contribution_records', verbose_name='任务')
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contribution_records',
        verbose_name='贡献者'
    )
    recorder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recorded_contributions',
        verbose_name='记录者'
    )
    
    contribution_type = models.CharField(max_length=30, choices=CONTRIBUTION_TYPE_CHOICES, verbose_name='贡献类型')
    score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='贡献分数'
    )
    weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='权重'
    )
    description = models.TextField(blank=True, verbose_name='贡献描述')
    evidence = models.TextField(blank=True, verbose_name='支撑证据')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        unique_together = ['task', 'contributor', 'recorder', 'contribution_type']
        verbose_name = '任务贡献记录'
        verbose_name_plural = '任务贡献记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', 'contributor']),
            models.Index(fields=['contribution_type', '-score']),
        ]
    
    def __str__(self):
        return f"{self.contributor.username} - {self.get_contribution_type_display()}: {self.score}分"
    
    @property
    def weighted_score(self):
        """加权分数"""
        return self.score * self.weight