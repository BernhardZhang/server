from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import json

class Project(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已完成'),
        ('pending', '待审核'),
        ('suspended', '暂停'),
    ]
    
    PROJECT_TYPE_CHOICES = [
        ('research', '研发项目'),
        ('academic', '学术项目'),
        ('design', '设计项目'),
        ('innovation', '创新实验'),
        ('development', '开发项目'),
        ('other', '其他'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(verbose_name='项目描述')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_projects', verbose_name='项目负责人')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectMembership', related_name='projects', verbose_name='项目成员')
    
    # 新增字段
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, default='other', verbose_name='项目类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='项目状态')
    tags = models.JSONField(default=list, blank=True, help_text='项目标签', verbose_name='项目标签')
    progress = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='项目进度'
    )
    task_count = models.IntegerField(default=0, verbose_name='任务总数')
    completed_tasks = models.IntegerField(default=0, verbose_name='已完成任务数')
    
    # 原有字段
    total_investment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='总投资额')
    valuation = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='项目估值')
    funding_rounds = models.IntegerField(default=0, verbose_name='融资轮次')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    is_public = models.BooleanField(default=False, verbose_name='是否公开展示')
    
    # 时间字段
    start_date = models.DateField(null=True, blank=True, verbose_name='开始时间')
    end_date = models.DateField(null=True, blank=True, verbose_name='结束时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()
    
    @property
    def tag_list(self):
        """返回标签列表"""
        if self.tags:
            # 如果是列表（新格式），直接返回
            if isinstance(self.tags, list):
                return self.tags
            # 如果是字符串（旧格式），按逗号分割
            elif isinstance(self.tags, str):
                return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []

class ProjectMembership(models.Model):
    ROLE_CHOICES = [
        ('owner', '项目负责人'),
        ('admin', '管理员'),
        ('member', '普通成员'),
        ('observer', '观察者'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name='角色')
    contribution_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='贡献比例')
    equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='股份比例')
    investment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='投资金额')
    contribution_description = models.TextField(blank=True, verbose_name='贡献描述')
    join_date = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')

    class Meta:
        unique_together = ['user', 'project']
        verbose_name = '项目成员'
        verbose_name_plural = '项目成员'

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"

class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files', verbose_name='项目')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='上传者')
    file = models.FileField(upload_to='project_files/%Y/%m/', verbose_name='文件')
    name = models.CharField(max_length=255, verbose_name='文件名')
    description = models.TextField(blank=True, verbose_name='文件描述')
    file_size = models.PositiveIntegerField(verbose_name='文件大小(字节)')
    file_type = models.CharField(max_length=50, verbose_name='文件类型')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    
    class Meta:
        verbose_name = '项目文件'
        verbose_name_plural = '项目文件'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"

class RatingSession(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已结束'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='rating_sessions', verbose_name='项目')
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name='所属项目')
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='project_assigned_tasks', 
        verbose_name='负责人'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='project_created_tasks',
        verbose_name='创建者'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    
    # 时间相关
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    due_date = models.DateField(null=True, blank=True, verbose_name='截止日期')
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
    
    # WISlab任务系统扩展字段
    role_weights = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='角色权重配置',
        help_text='存储各角色在任务中的权重，格式：{"user_id": weight}'
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TaskAssignment',
        related_name='assigned_tasks_extended',
        verbose_name='任务负责人(多人)'
    )
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
    
    # 标签和分类
    tags = models.JSONField(default=list, blank=True, help_text='任务标签', verbose_name='任务标签')
    category = models.CharField(max_length=50, blank=True, verbose_name='任务分类')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.title}"
    
    @property
    def tag_list(self):
        """返回标签列表"""
        if self.tags:
            # 如果是列表（新格式），直接返回
            if isinstance(self.tags, list):
                return self.tags
            # 如果是字符串（旧格式），按逗号分割
            elif isinstance(self.tags, str):
                return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def is_overdue(self):
        """检查任务是否过期"""
        if self.due_date and self.status not in ['completed', 'cancelled']:
            from django.utils import timezone
            return timezone.now().date() > self.due_date
        return False
    
    def save(self, *args, **kwargs):
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
    
    def calculate_time_coefficient(self):
        """计算时效系数"""
        if not self.due_date or not self.completed_at:
            return Decimal('1.00')
        
        # 计算完成时间与截止时间的差值（天数）
        completed_date = self.completed_at.date()
        days_diff = (completed_date - self.due_date).days
        
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
        """计算系统分：任务占比 × 角色权重 × 时效系数"""
        if self.status != 'completed' or not self.assignee:
            return Decimal('0.00')
        
        # 基础分数（任务在项目中的占比，可以根据需要调整）
        base_score = Decimal('100.00')  # 基础100分
        
        # 获取角色权重
        assignee_id = str(self.assignee.id)
        role_weight = Decimal(str(self.role_weights.get(assignee_id, 1.0)))
        
        # 计算系统分
        system_score = base_score * role_weight * self.time_coefficient
        return round(system_score, 2)

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='任务')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_task_comments', verbose_name='作者')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '任务评论'
        verbose_name_plural = '任务评论'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.task.title} - {self.author.username}: {self.content[:50]}"

class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', verbose_name='任务')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_task_attachments', verbose_name='上传者')
    file = models.FileField(upload_to='task_attachments/%Y/%m/', verbose_name='附件')
    name = models.CharField(max_length=255, verbose_name='文件名')
    description = models.TextField(blank=True, verbose_name='文件描述')
    file_size = models.PositiveIntegerField(verbose_name='文件大小(字节)')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    
    class Meta:
        verbose_name = '任务附件'
        verbose_name_plural = '任务附件'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.task.title} - {self.name}"

class ProjectLog(models.Model):
    LOG_TYPE_CHOICES = [
        ('project_created', '项目创建'),
        ('project_updated', '项目更新'),
        ('member_joined', '成员加入'),
        ('member_left', '成员离开'),
        ('member_role_changed', '成员角色变更'),
        ('task_created', '任务创建'),
        ('task_updated', '任务更新'),
        ('task_completed', '任务完成'),
        ('task_deleted', '任务删除'),
        ('file_uploaded', '文件上传'),
        ('file_deleted', '文件删除'),
        ('rating_created', '评分创建'),
        ('rating_completed', '评分完成'),
        ('comment_added', '评论添加'),
        ('milestone_reached', '里程碑达成'),
        ('status_changed', '状态变更'),
        ('other', '其他操作'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs', verbose_name='项目')
    log_type = models.CharField(max_length=50, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='操作用户')
    title = models.CharField(max_length=200, verbose_name='日志标题')
    description = models.TextField(blank=True, verbose_name='详细描述')
    
    # 相关对象信息（可选）
    related_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关任务')
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='project_logs_about',
        verbose_name='相关用户'
    )
    
    # 变更数据（JSON格式存储变更前后的值）
    changes = models.JSONField(default=dict, blank=True, verbose_name='变更内容')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '项目日志'
        verbose_name_plural = '项目日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['log_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.project.name} - {self.title}"
    
    @classmethod
    def create_log(cls, project, log_type, user, title, description='', **kwargs):
        """便捷方法创建项目日志"""
        return cls.objects.create(
            project=project,
            log_type=log_type,
            user=user,
            title=title,
            description=description,
            **kwargs
        )

class Points(models.Model):
    """用户积分总表"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    total_points = models.IntegerField(default=0, verbose_name='总积分')
    available_points = models.IntegerField(default=0, verbose_name='可用积分')
    used_points = models.IntegerField(default=0, verbose_name='已使用积分')
    level = models.IntegerField(default=1, verbose_name='积分等级')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户积分'
        verbose_name_plural = '用户积分'
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points}分"
    
    @property
    def level_name(self):
        """根据积分获取等级名称"""
        if self.total_points >= 10000:
            return "钻石"
        elif self.total_points >= 5000:
            return "黄金"
        elif self.total_points >= 2000:
            return "白银"
        elif self.total_points >= 500:
            return "青铜"
        else:
            return "新手"
    
    def add_points(self, points, reason="", related_project=None, related_task=None):
        """增加积分"""
        self.total_points += points
        self.available_points += points
        self.level = self.calculate_level()
        self.save()
        
        # 记录积分历史
        PointsHistory.objects.create(
            user=self.user,
            change_type='earn',
            points=points,
            reason=reason,
            balance_after=self.total_points,
            related_project=related_project,
            related_task=related_task
        )
    
    def use_points(self, points, reason="", related_project=None):
        """使用积分"""
        if self.available_points < points:
            raise ValueError("积分不足")
        
        self.available_points -= points
        self.used_points += points
        self.save()
        
        # 记录积分历史
        PointsHistory.objects.create(
            user=self.user,
            change_type='spend',
            points=-points,
            reason=reason,
            balance_after=self.total_points,
            related_project=related_project
        )
    
    def calculate_level(self):
        """根据总积分计算等级"""
        if self.total_points >= 10000:
            return 5  # 钻石
        elif self.total_points >= 5000:
            return 4  # 黄金
        elif self.total_points >= 2000:
            return 3  # 白银
        elif self.total_points >= 500:
            return 2  # 青铜
        else:
            return 1  # 新手

class PointsHistory(models.Model):
    """积分变动历史"""
    CHANGE_TYPE_CHOICES = [
        ('earn', '获得'),
        ('spend', '消费'),
        ('transfer', '转账'),
        ('reward', '奖励'),
        ('penalty', '扣除'),
        ('refund', '退还'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name='变动类型')
    points = models.IntegerField(verbose_name='积分变动')  # 正数为增加，负数为减少
    reason = models.CharField(max_length=200, verbose_name='变动原因')
    balance_after = models.IntegerField(verbose_name='变动后余额')
    
    # 关联信息
    related_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关项目')
    related_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关任务')
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='points_from',
        verbose_name='相关用户'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '积分历史'
        verbose_name_plural = '积分历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['change_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} {self.get_change_type_display()} {abs(self.points)}分"

class ProjectPoints(models.Model):
    """项目积分分配"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='point_allocations', verbose_name='项目')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    points = models.IntegerField(default=0, verbose_name='分配积分')
    contribution_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='贡献评分')
    allocation_reason = models.TextField(blank=True, verbose_name='分配原因')
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='point_allocations_made',
        verbose_name='分配者'
    )
    is_final = models.BooleanField(default=False, verbose_name='是否最终分配')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        unique_together = ['project', 'user']
        verbose_name = '项目积分分配'
        verbose_name_plural = '项目积分分配'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.user.username}: {self.points}分"

class PointsEvaluation(models.Model):
    """功分互评"""
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='evaluations', verbose_name='项目')
    name = models.CharField(max_length=200, verbose_name='评分名称')
    description = models.TextField(blank=True, verbose_name='评分说明')
    total_points = models.IntegerField(default=100, verbose_name='总分配积分')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='创建者')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='evaluations_participated',
        verbose_name='参与成员'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '功分互评'
        verbose_name_plural = '功分互评'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
    
    @property
    def participant_count(self):
        return self.participants.count()
    
    @property
    def evaluation_count(self):
        return self.evaluation_records.count()
    
    def is_user_participated(self, user):
        """检查用户是否已参与评分"""
        return self.evaluation_records.filter(evaluator=user).exists()
    
    def calculate_final_scores(self):
        """计算最终评分结果"""
        if self.status != 'completed':
            return {}
        
        results = {}
        participants = self.participants.all()
        
        for participant in participants:
            # 获取该用户收到的所有评分
            evaluations = self.evaluation_records.filter(evaluated_user=participant)
            if evaluations.exists():
                total_score = sum(eval.score for eval in evaluations)
                avg_score = total_score / evaluations.count()
                results[participant.id] = {
                    'user': participant,
                    'total_score': total_score,
                    'average_score': round(avg_score, 2),
                    'evaluation_count': evaluations.count()
                }
        
        return results

class EvaluationRecord(models.Model):
    """评分记录"""
    evaluation = models.ForeignKey(PointsEvaluation, on_delete=models.CASCADE, related_name='evaluation_records', verbose_name='评分活动')
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='project_evaluations_given',
        verbose_name='评分者'
    )
    evaluated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='project_evaluations_received',
        verbose_name='被评分者'
    )
    score = models.IntegerField(verbose_name='评分')
    comment = models.TextField(blank=True, verbose_name='评分意见')
    criteria_scores = models.JSONField(default=dict, blank=True, verbose_name='各项评分')  # 存储各个评分维度的分数
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评分时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        unique_together = ['evaluation', 'evaluator', 'evaluated_user']
        verbose_name = '评分记录'
        verbose_name_plural = '评分记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.evaluator.username} 给 {self.evaluated_user.username} 评分: {self.score}"

class TaskAssignment(models.Model):
    """任务分配关系表"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name='任务')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    role_weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('1.00'),
        verbose_name='角色权重'
    )
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
    total_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='总分'
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='分配时间')
    
    class Meta:
        unique_together = ['task', 'user']
        verbose_name = '任务分配'
        verbose_name_plural = '任务分配'
    
    def __str__(self):
        return f"{self.task.title} - {self.user.username}"
    
    def calculate_scores(self):
        """计算该用户在该任务中的分数"""
        if self.task.status != 'completed':
            return
        
        # 计算系统分
        base_score = Decimal('100.00')
        self.system_score = base_score * self.role_weight * self.task.time_coefficient
        
        # 功分需要从评分记录中计算
        # 这里暂时保持原值，会在评分完成后更新
        
        # 计算总分
        self.total_score = self.system_score + self.function_score
        self.save()

class WislabMembership(models.Model):
    """WISlab会员系统"""
    MEMBERSHIP_TYPES = [
        ('normal', '普通会员'),
        ('vip', 'VIP会员'),
        ('premium', '高级会员'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wislab_membership',
        verbose_name='用户'
    )
    membership_type = models.CharField(
        max_length=20, 
        choices=MEMBERSHIP_TYPES, 
        default='normal',
        verbose_name='会员类型'
    )
    project_limit = models.IntegerField(
        default=5,
        verbose_name='项目限制',
        help_text='普通会员最多参与的项目数量'
    )
    expire_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='会员到期时间'
    )
    total_points = models.IntegerField(default=0, verbose_name='总积分')
    available_points = models.IntegerField(default=0, verbose_name='可用积分')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'WISlab会员'
        verbose_name_plural = 'WISlab会员'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_membership_type_display()}"
    
    @property
    def is_vip(self):
        """检查是否为VIP会员"""
        return self.membership_type in ['vip', 'premium']
    
    @property
    def current_project_count(self):
        """当前参与的项目数量"""
        return self.user.projects.filter(status='active').count()
    
    def can_join_project(self):
        """检查是否可以加入新项目"""
        if self.is_vip:
            return True
        return self.current_project_count < self.project_limit
    
    def is_membership_valid(self):
        """检查会员是否有效"""
        if not self.is_active:
            return False
        if self.expire_date and timezone.now() > self.expire_date:
            return False
        return True

class ProjectDataAnalysis(models.Model):
    """项目数据分析"""
    project = models.OneToOneField(
        Project, 
        on_delete=models.CASCADE, 
        related_name='data_analysis',
        verbose_name='项目'
    )
    total_system_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='总系统分'
    )
    total_function_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='总功分'
    )
    total_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='总分'
    )
    avg_system_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='平均系统分'
    )
    avg_function_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='平均功分'
    )
    member_scores = models.JSONField(
        default=dict,
        verbose_name='成员分数详情',
        help_text='存储每个成员的详细分数信息'
    )
    analysis_summary = models.TextField(blank=True, verbose_name='分析摘要')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='最后更新时间')
    
    class Meta:
        verbose_name = '项目数据分析'
        verbose_name_plural = '项目数据分析'
    
    def __str__(self):
        return f"{self.project.name} - 数据分析"
    
    def update_analysis(self):
        """更新项目分析数据"""
        members = self.project.members.all()
        member_count = members.count()
        
        if member_count == 0:
            return
        
        total_system = Decimal('0.00')
        total_function = Decimal('0.00')
        member_data = {}
        
        for member in members:
            # 获取该成员在项目中所有任务的分数
            task_assignments = TaskAssignment.objects.filter(
                task__project=self.project,
                user=member
            )
            
            member_system_score = sum(
                assignment.system_score for assignment in task_assignments
            )
            member_function_score = sum(
                assignment.function_score for assignment in task_assignments
            )
            member_total_score = member_system_score + member_function_score
            
            total_system += member_system_score
            total_function += member_function_score
            
            member_data[str(member.id)] = {
                'username': member.username,
                'system_score': float(member_system_score),
                'function_score': float(member_function_score),
                'total_score': float(member_total_score),
                'task_count': task_assignments.count()
            }
        
        self.total_system_score = total_system
        self.total_function_score = total_function
        self.total_score = total_system + total_function
        self.avg_system_score = total_system / member_count if member_count > 0 else Decimal('0.00')
        self.avg_function_score = total_function / member_count if member_count > 0 else Decimal('0.00')
        self.member_scores = member_data
        
        self.save()

class MemberRecruitment(models.Model):
    """成员招募"""
    STATUS_CHOICES = [
        ('open', '开放招募'),
        ('paused', '暂停招募'),
        ('closed', '结束招募'),
    ]
    
    SKILL_LEVEL_CHOICES = [
        ('beginner', '初级'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
        ('expert', '专家'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='recruitments', verbose_name='项目')
    title = models.CharField(max_length=200, verbose_name='招募标题')
    description = models.TextField(verbose_name='招募描述')
    required_skills = models.JSONField(default=list, verbose_name='所需技能')
    skill_level_required = models.CharField(
        max_length=20, 
        choices=SKILL_LEVEL_CHOICES,
        default='intermediate',
        verbose_name='技能等级要求'
    )
    positions_needed = models.IntegerField(default=1, verbose_name='招募人数')
    positions_filled = models.IntegerField(default=0, verbose_name='已招募人数')
    
    # 工作安排
    work_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', '全职'),
            ('part_time', '兼职'),
            ('contract', '合同工'),
            ('volunteer', '志愿者'),
        ],
        default='part_time',
        verbose_name='工作类型'
    )
    expected_commitment = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='预期投入时间',
        help_text='如：每周10小时'
    )
    
    # 报酬与股份
    salary_range = models.CharField(max_length=100, blank=True, verbose_name='薪资范围')
    equity_percentage_min = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name='最小股份比例'
    )
    equity_percentage_max = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name='最大股份比例'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='招募状态')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='截止时间')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='发布者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='发布时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '成员招募'
        verbose_name_plural = '成员招募'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.title}"
    
    @property
    def is_active(self):
        """检查招募是否仍然有效"""
        if self.status != 'open':
            return False
        if self.deadline and timezone.now() > self.deadline:
            return False
        return self.positions_filled < self.positions_needed
    
    @property
    def application_count(self):
        """申请数量"""
        return self.applications.count()

class MemberApplication(models.Model):
    """成员申请"""
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('reviewing', '审核中'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('withdrawn', '已撤回'),
    ]
    
    recruitment = models.ForeignKey(
        MemberRecruitment, 
        on_delete=models.CASCADE, 
        related_name='applications',
        verbose_name='招募信息'
    )
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='申请人')
    cover_letter = models.TextField(verbose_name='申请理由')
    skills = models.JSONField(default=list, verbose_name='技能清单')
    experience = models.TextField(blank=True, verbose_name='相关经验')
    portfolio_url = models.URLField(blank=True, verbose_name='作品集链接')
    expected_commitment = models.CharField(max_length=100, blank=True, verbose_name='可投入时间')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='申请状态')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_applications',
        verbose_name='审核人'
    )
    review_notes = models.TextField(blank=True, verbose_name='审核备注')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        unique_together = ['recruitment', 'applicant']
        verbose_name = '成员申请'
        verbose_name_plural = '成员申请'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.applicant.username} 申请 {self.recruitment.title}"
    
    def approve(self, reviewer, equity_percentage=0.00, role='member'):
        """批准申请"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        
        # 创建项目成员关系
        membership, created = ProjectMembership.objects.get_or_create(
            user=self.applicant,
            project=self.recruitment.project,
            defaults={
                'role': role,
                'equity_percentage': equity_percentage,
            }
        )
        
        # 更新招募信息
        self.recruitment.positions_filled += 1
        if self.recruitment.positions_filled >= self.recruitment.positions_needed:
            self.recruitment.status = 'closed'
        self.recruitment.save()
        
        return membership
    
    def reject(self, reviewer, notes=''):
        """拒绝申请"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()

class ProjectRevenue(models.Model):
    """项目收益"""
    REVENUE_TYPE_CHOICES = [
        ('investment', '投资收入'),
        ('sales', '销售收入'),
        ('service', '服务收入'),
        ('licensing', '授权收入'),
        ('grant', '资助资金'),
        ('other', '其他收入'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='revenues', verbose_name='项目')
    revenue_type = models.CharField(max_length=20, choices=REVENUE_TYPE_CHOICES, verbose_name='收益类型')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='收益金额')
    description = models.TextField(verbose_name='收益描述')
    source = models.CharField(max_length=200, blank=True, verbose_name='收益来源')
    
    # 成本
    associated_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='相关成本')
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='净收益')
    
    # 时间
    revenue_date = models.DateField(verbose_name='收益日期')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='记录人')
    
    # 分配状态
    is_distributed = models.BooleanField(default=False, verbose_name='是否已分配')
    distribution_date = models.DateTimeField(null=True, blank=True, verbose_name='分配时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '项目收益'
        verbose_name_plural = '项目收益'
        ordering = ['-revenue_date']
    
    def __str__(self):
        return f"{self.project.name} - {self.get_revenue_type_display()}: ¥{self.amount}"
    
    def save(self, *args, **kwargs):
        # 计算净收益
        self.net_amount = self.amount - self.associated_costs
        super().save(*args, **kwargs)
    
    def distribute_revenue(self):
        """根据股份比例分配收益"""
        if self.is_distributed:
            return False
        
        memberships = self.project.projectmembership_set.filter(is_active=True)
        total_equity = sum(m.equity_percentage for m in memberships)
        
        if total_equity <= 0:
            return False
        
        distributions = []
        for membership in memberships:
            if membership.equity_percentage > 0:
                distribution_amount = (membership.equity_percentage / total_equity) * self.net_amount
                distribution = RevenueDistribution.objects.create(
                    revenue=self,
                    member=membership.user,
                    membership=membership,
                    amount=distribution_amount,
                    equity_percentage_at_time=membership.equity_percentage
                )
                distributions.append(distribution)
        
        self.is_distributed = True
        self.distribution_date = timezone.now()
        self.save()
        
        return distributions

class RevenueDistribution(models.Model):
    """收益分配记录"""
    revenue = models.ForeignKey(ProjectRevenue, on_delete=models.CASCADE, related_name='distributions', verbose_name='项目收益')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='成员')
    membership = models.ForeignKey(ProjectMembership, on_delete=models.CASCADE, verbose_name='成员关系')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='分配金额')
    equity_percentage_at_time = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='分配时股份比例')
    
    # 支付状态
    is_paid = models.BooleanField(default=False, verbose_name='是否已支付')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='支付时间')
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='支付方式')
    payment_reference = models.CharField(max_length=100, blank=True, verbose_name='支付凭证号')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='分配时间')
    
    class Meta:
        unique_together = ['revenue', 'member']
        verbose_name = '收益分配'
        verbose_name_plural = '收益分配'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.username} - {self.revenue.project.name}: ¥{self.amount}"
    
    def mark_as_paid(self, payment_method='', payment_reference=''):
        """标记为已支付"""
        self.is_paid = True
        self.paid_at = timezone.now()
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.save()

class TaskTeam(models.Model):
    """任务团队"""
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='team', verbose_name='任务')
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TaskTeamMembership',
        related_name='task_teams',
        verbose_name='团队成员'
    )
    team_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='led_task_teams',
        verbose_name='团队负责人'
    )
    max_members = models.IntegerField(default=2, verbose_name='最大成员数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '任务团队'
        verbose_name_plural = '任务团队'
    
    def __str__(self):
        return f"{self.task.title} - 团队"
    
    @property
    def member_count(self):
        return self.members.count()
    
    def can_add_member(self):
        return self.member_count < self.max_members

class TaskTeamMembership(models.Model):
    """任务团队成员关系"""
    ROLE_CHOICES = [
        ('leader', '团队负责人'),
        ('member', '团队成员'),
        ('reviewer', '评审员'),
    ]
    
    team = models.ForeignKey(TaskTeam, on_delete=models.CASCADE, verbose_name='任务团队')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name='角色')
    
    # 工作分配权重
    work_weight = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('1.00'),
        verbose_name='工作权重',
        help_text='团队内工作量分配权重'
    )
    
    # 评估分数
    peer_evaluation_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='同行评分'
    )
    self_evaluation_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name='自评分数'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    
    class Meta:
        unique_together = ['team', 'user']
        verbose_name = '任务团队成员'
        verbose_name_plural = '任务团队成员'
    
    def __str__(self):
        return f"{self.team.task.title} - {self.user.username}"