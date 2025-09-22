from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Project, ProjectMembership, ProjectLog
from decimal import Decimal

User = get_user_model()

@receiver(post_save, sender=Project)
def log_project_activity(sender, instance, created, **kwargs):
    """记录项目创建和更新日志"""
    if created:
        ProjectLog.create_log(
            project=instance,
            log_type='project_created',
            user=instance.owner,
            title=f'创建了项目 "{instance.name}"',
            description=f'项目描述：{instance.description[:100]}...' if len(instance.description) > 100 else instance.description
        )
    else:
        # 对于更新，我们需要在pre_save中获取旧值
        pass

@receiver(pre_save, sender=Project)
def track_project_changes(sender, instance, **kwargs):
    """跟踪项目变更"""
    if instance.pk:  # 只处理更新，不处理创建
        try:
            old_instance = Project.objects.get(pk=instance.pk)
            changes = {}

            # 检查各个字段的变更
            if old_instance.name != instance.name:
                changes['name'] = {'old': old_instance.name, 'new': instance.name}

            if old_instance.description != instance.description:
                changes['description'] = {'old': old_instance.description, 'new': instance.description}

            if old_instance.status != instance.status:
                changes['status'] = {'old': old_instance.status, 'new': instance.status}

            if old_instance.progress != instance.progress:
                changes['progress'] = {'old': old_instance.progress, 'new': instance.progress}

            # 如果有变更，保存到实例中，在post_save中使用
            if changes:
                instance._changes = changes
        except Project.DoesNotExist:
            pass

@receiver(post_save, sender=Project)
def log_project_updates(sender, instance, created, **kwargs):
    """记录项目更新日志"""
    if not created and hasattr(instance, '_changes'):
        changes = instance._changes
        change_descriptions = []

        for field, change in changes.items():
            if field == 'name':
                change_descriptions.append(f'项目名称从 "{change["old"]}" 改为 "{change["new"]}"')
            elif field == 'description':
                change_descriptions.append('更新了项目描述')
            elif field == 'status':
                change_descriptions.append(f'项目状态从 "{change["old"]}" 改为 "{change["new"]}"')
            elif field == 'progress':
                change_descriptions.append(f'项目进度从 {change["old"]}% 更新为 {change["new"]}%')

        if change_descriptions:
            # 获取当前用户（这里需要通过其他方式获取，因为信号中没有request）
            # 暂时使用项目所有者作为操作用户
            ProjectLog.create_log(
                project=instance,
                log_type='project_updated',
                user=instance.owner,  # 实际使用中应该是当前操作的用户
                title='更新了项目信息',
                description='; '.join(change_descriptions),
                changes=changes
            )

@receiver(post_save, sender=ProjectMembership)
def log_membership_activity(sender, instance, created, **kwargs):
    """记录成员加入/角色变更日志"""
    if created:
        ProjectLog.create_log(
            project=instance.project,
            log_type='member_joined',
            user=instance.user,
            title=f'{instance.user.username} 加入了项目',
            description=f'角色：{instance.get_role_display()}',
            related_user=instance.user,
            metadata={
                'role': instance.role,
                'contribution_percentage': str(instance.contribution_percentage)
            }
        )

@receiver(post_delete, sender=ProjectMembership)
def log_membership_deletion(sender, instance, **kwargs):
    """记录成员离开日志"""
    ProjectLog.create_log(
        project=instance.project,
        log_type='member_left',
        user=instance.user,
        title=f'{instance.user.username} 离开了项目',
        description=f'原角色：{instance.get_role_display()}',
        related_user=instance.user,
        metadata={
            'role': instance.role,
            'contribution_percentage': str(instance.contribution_percentage)
        }
    )

def calculate_project_progress(project):
    """计算项目进度基于任务完成情况"""
    from apps.tasks.models import Task

    # 获取项目的所有任务
    tasks = Task.objects.filter(project=project)

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
            return min(max(result, 0), 100)  # 确保在0-100范围内

    # 方法2: 基于任务完成状态计算（如果没有工时信息）
    completed_tasks = tasks.filter(status='completed').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    total_tasks = tasks.count()

    # 已完成任务算100%，进行中任务算50%，其他算0%
    progress_value = int(((completed_tasks * 100) + (in_progress_tasks * 50)) / total_tasks)
    return min(max(progress_value, 0), 100)  # 确保在0-100范围内

# 监听任务变更以更新项目进度
@receiver(post_save, sender='tasks.Task')
def update_project_progress_on_task_change(sender, instance, **kwargs):
    """当任务状态或进度变更时，自动更新项目进度"""
    if instance.project:
        new_progress = calculate_project_progress(instance.project)
        if instance.project.progress != new_progress:
            # 避免触发循环信号
            Project.objects.filter(pk=instance.project.pk).update(progress=new_progress)

@receiver(post_delete, sender='tasks.Task')
def update_project_progress_on_task_delete(sender, instance, **kwargs):
    """当任务被删除时，自动更新项目进度"""
    if instance.project:
        new_progress = calculate_project_progress(instance.project)
        if instance.project.progress != new_progress:
            # 避免触发循环信号
            Project.objects.filter(pk=instance.project.pk).update(progress=new_progress)