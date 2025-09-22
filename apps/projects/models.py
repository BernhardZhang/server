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

    # 原有字段
    total_investment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='总投资额')
    valuation = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='项目估值')
    funding_rounds = models.IntegerField(default=0, verbose_name='融资轮次')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    is_public = models.BooleanField(default=False, verbose_name='是否公开展示')

    # 邀请码相关字段
    invite_code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='邀请码')
    invite_code_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='邀请码过期时间')
    invite_code_enabled = models.BooleanField(default=True, verbose_name='是否启用邀请码')

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
        return self.projectmembership_set.filter(is_active=True).count()

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
    def calculated_progress(self):
        """基于任务计算的项目进度"""
        from apps.tasks.models import Task
        from decimal import Decimal

        # 获取项目的所有任务
        tasks = Task.objects.filter(project=self)

        if not tasks.exists():
            return 0

        # 方法1: 使用预估工时作为权重计算加权平均进度
        tasks_with_hours = tasks.filter(estimated_hours__gt=0)

        if tasks_with_hours.exists():
            # 使用工时加权计算
            weighted_progress = Decimal('0')
            total_weight = Decimal('0')

            for task in tasks_with_hours:
                hours = task.estimated_hours or Decimal('0')
                progress = Decimal(str(task.progress or 0))
                weighted_progress += (progress * hours)
                total_weight += hours

            if total_weight > 0:
                result = int(weighted_progress / total_weight)
                return min(max(result, 0), 100)

        # 方法2: 基于任务完成状态计算（如果没有工时信息）
        completed_tasks = tasks.filter(status='completed').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        total_tasks = tasks.count()

        # 已完成任务算100%，进行中任务算50%，其他算0%
        progress_value = int(((completed_tasks * 100) + (in_progress_tasks * 50)) / total_tasks)
        return min(max(progress_value, 0), 100)

    def generate_invite_code(self):
        """生成邀请码"""
        import random
        import string
        from django.utils import timezone

        # 生成8位随机邀请码
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # 确保邀请码唯一
        while Project.objects.filter(invite_code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        self.invite_code = code
        # 设置7天过期时间
        self.invite_code_expires_at = timezone.now() + timezone.timedelta(days=7)
        self.save(update_fields=['invite_code', 'invite_code_expires_at'])

        return code

    def is_invite_code_valid(self):
        """检查邀请码是否有效"""
        if not self.invite_code or not self.invite_code_enabled:
            return False

        if self.invite_code_expires_at and timezone.now() > self.invite_code_expires_at:
            return False

        return True

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

class ProjectLog(models.Model):
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

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs', verbose_name='项目')
    log_type = models.CharField(max_length=50, choices=LOG_TYPE_CHOICES, verbose_name='日志类型')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='操作用户')
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
        related_name='project_logs_about',
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
            models.Index(fields=['log_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.title}"

    @classmethod
    def create_log(cls, project, log_type, user, title, description='',
                   action_method='', action_function='', ip_address=None,
                   user_agent='', **kwargs):
        """便捷方法创建项目日志"""
        return cls.objects.create(
            project=project,
            log_type=log_type,
            user=user,
            title=title,
            description=description,
            action_method=action_method,
            action_function=action_function,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs
        )

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