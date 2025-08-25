from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import (
    Project, ProjectMembership, Task, ProjectLog, TaskComment, TaskAttachment,
    Points, PointsHistory, ProjectPoints, PointsEvaluation, EvaluationRecord
)

User = get_user_model()

# 积分系统信号处理

@receiver(post_save, sender=User)
def create_user_points(sender, instance, created, **kwargs):
    """用户创建时自动创建积分记录"""
    if created:
        Points.objects.get_or_create(user=instance)

@receiver(post_save, sender=Task)
def award_task_points(sender, instance, created, **kwargs):
    """任务完成时自动奖励积分"""
    if not created and instance.status == 'completed' and hasattr(instance, '_old_status'):
        if instance._old_status != 'completed':
            # 任务完成，奖励积分
            assignee = instance.assignee or instance.creator
            if assignee:
                points_obj, _ = Points.objects.get_or_create(user=assignee)
                
                # 根据任务复杂度和优先级计算积分
                base_points = 10
                if instance.priority == 'urgent':
                    base_points = 25
                elif instance.priority == 'high':
                    base_points = 20
                elif instance.priority == 'medium':
                    base_points = 15
                
                # 根据预估工时调整积分
                if instance.estimated_hours:
                    hour_bonus = min(int(instance.estimated_hours) * 2, 20)  # 最多额外20分
                    base_points += hour_bonus
                
                points_obj.add_points(
                    points=base_points,
                    reason=f'完成任务: {instance.title}',
                    related_project=instance.project,
                    related_task=instance
                )

@receiver(post_save, sender=TaskComment)
def award_comment_points(sender, instance, created, **kwargs):
    """添加评论时奖励少量积分"""
    if created:
        points_obj, _ = Points.objects.get_or_create(user=instance.author)
        points_obj.add_points(
            points=2,
            reason=f'添加评论: {instance.content[:20]}...',
            related_project=instance.task.project,
            related_task=instance.task
        )

@receiver(post_save, sender=Project)
def award_project_creation_points(sender, instance, created, **kwargs):
    """项目创建时奖励积分"""
    if created:
        points_obj, _ = Points.objects.get_or_create(user=instance.owner)
        points_obj.add_points(
            points=50,
            reason=f'创建项目: {instance.name}',
            related_project=instance
        )

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

@receiver(post_save, sender=Task)
def log_task_activity(sender, instance, created, **kwargs):
    """记录任务创建和更新日志"""
    if created:
        ProjectLog.create_log(
            project=instance.project,
            log_type='task_created',
            user=instance.creator,
            title=f'创建了任务 "{instance.title}"',
            description=f'负责人：{instance.assignee.username if instance.assignee else "未分配"}',
            related_task=instance,
            related_user=instance.assignee,
            metadata={
                'status': instance.status,
                'priority': instance.priority,
                'progress': instance.progress
            }
        )
    else:
        # 检查是否是任务完成
        if instance.status == 'completed' and hasattr(instance, '_old_status'):
            if instance._old_status != 'completed':
                ProjectLog.create_log(
                    project=instance.project,
                    log_type='task_completed',
                    user=instance.assignee or instance.creator,  # 使用负责人或创建者
                    title=f'完成了任务 "{instance.title}"',
                    description=f'任务进度：{instance.progress}%',
                    related_task=instance,
                    related_user=instance.assignee,
                    metadata={
                        'completed_at': instance.completed_at.isoformat() if instance.completed_at else None,
                        'progress': instance.progress
                    }
                )

@receiver(pre_save, sender=Task)
def track_task_status(sender, instance, **kwargs):
    """跟踪任务状态变更"""
    if instance.pk:
        try:
            old_instance = Task.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Task.DoesNotExist:
            pass

@receiver(post_delete, sender=Task)
def log_task_deletion(sender, instance, **kwargs):
    """记录任务删除日志"""
    ProjectLog.create_log(
        project=instance.project,
        log_type='task_deleted',
        user=instance.creator,  # 使用创建者，因为删除时可能没有当前用户信息
        title=f'删除了任务 "{instance.title}"',
        description=f'任务状态：{instance.get_status_display()}，进度：{instance.progress}%',
        metadata={
            'deleted_task_data': {
                'title': instance.title,
                'status': instance.status,
                'priority': instance.priority,
                'progress': instance.progress,
                'assignee': instance.assignee.username if instance.assignee else None
            }
        }
    )

@receiver(post_save, sender=TaskComment)
def log_comment_activity(sender, instance, created, **kwargs):
    """记录任务评论日志"""
    if created:
        ProjectLog.create_log(
            project=instance.task.project,
            log_type='comment_added',
            user=instance.author,
            title=f'在任务 "{instance.task.title}" 中添加了评论',
            description=instance.content[:100] + '...' if len(instance.content) > 100 else instance.content,
            related_task=instance.task,
            metadata={
                'comment_id': instance.id,
                'content_length': len(instance.content)
            }
        )

@receiver(post_save, sender=TaskAttachment)
def log_attachment_upload(sender, instance, created, **kwargs):
    """记录文件上传日志"""
    if created:
        ProjectLog.create_log(
            project=instance.task.project,
            log_type='file_uploaded',
            user=instance.uploaded_by,
            title=f'在任务 "{instance.task.title}" 中上传了文件 "{instance.name}"',
            description=f'文件大小：{instance.file_size} 字节',
            related_task=instance.task,
            metadata={
                'file_name': instance.name,
                'file_size': instance.file_size,
                'attachment_id': instance.id
            }
        )

@receiver(post_delete, sender=TaskAttachment)
def log_attachment_deletion(sender, instance, **kwargs):
    """记录文件删除日志"""
    ProjectLog.create_log(
        project=instance.task.project,
        log_type='file_deleted',
        user=instance.uploaded_by,  # 使用上传者，实际应该是删除者
        title=f'删除了任务 "{instance.task.title}" 中的文件 "{instance.name}"',
        description=f'文件大小：{instance.file_size} 字节',
        related_task=instance.task,
        metadata={
            'deleted_file_data': {
                'name': instance.name,
                'file_size': instance.file_size,
                'uploaded_at': instance.uploaded_at.isoformat()
            }
        }
    )