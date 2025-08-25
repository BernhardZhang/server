from rest_framework import generics, permissions, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Count, Avg
from django.utils import timezone
from decimal import Decimal
from .models import (Task, TaskComment, TaskAttachment, TaskEvaluation, TaskEvaluationSession, 
                     TaskLog, TaskUserLog, TaskUserLogAttachment, TaskTeamMeritCalculation, 
                     TaskTeamMeritResult, TaskContributionRecord)
from .serializers import (TaskSerializer, TaskCreateSerializer, TaskCommentSerializer, 
                         TaskCommentCreateSerializer, TaskAttachmentSerializer, 
                         TaskAttachmentCreateSerializer, TaskEvaluationSerializer, 
                         TaskEvaluationSessionSerializer, TaskLogSerializer,
                         TaskUserLogSerializer, TaskUserLogCreateSerializer, TaskUserLogAttachmentSerializer)

class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskSerializer

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.query_params.get('status')
        priority_filter = self.request.query_params.get('priority')
        project_id = self.request.query_params.get('project')
        assignee_id = self.request.query_params.get('assignee')
        
        # 用户可以看到自己创建的、被分配的、或项目相关的任务
        queryset = Task.objects.filter(
            Q(creator=user) | Q(assignee=user) | Q(project__members=user)
        ).distinct()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)
            
        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        # 使用CreateSerializer验证和创建
        create_serializer = TaskCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        
        # 执行创建逻辑
        self.perform_create(create_serializer)
        
        # 使用完整的TaskSerializer返回创建的任务
        task = create_serializer.instance
        response_serializer = TaskSerializer(task)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        # 确保用户是项目成员才能创建任务
        project = serializer.validated_data.get('project')
        if project and not project.members.filter(id=self.request.user.id).exists():
            raise serializers.ValidationError('只有项目成员才能创建任务')
        
        # 保存任务
        task = serializer.save(creator=self.request.user)
        
        # 处理文件上传
        files = self.request.FILES.getlist('files')
        for uploaded_file in files:
            TaskAttachment.objects.create(
                task=task,
                file=uploaded_file,
                filename=uploaded_file.name,
                uploaded_by=self.request.user,
                file_size=uploaded_file.size
            )
        
        # 记录创建日志
        TaskLog.log_action(
            task=task,
            user=self.request.user,
            action='created',
            description=f'创建了任务：{task.title}',
            request=self.request
        )
        
        # 如果有文件上传，记录上传日志
        if files:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='attachment_uploaded',
                description=f'上传了 {len(files)} 个文件',
                new_value={
                    'file_count': len(files),
                    'filenames': [f.name for f in files]
                },
                request=self.request
            )
        
        # 如果分配了任务执行者，记录分配日志
        if task.assignee:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='assigned',
                description=f'将任务分配给：{task.assignee.username}',
                new_value={'assignee': task.assignee.username, 'assignee_id': task.assignee.id},
                request=self.request
            )

class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(
            Q(creator=user) | Q(assignee=user) | Q(project__members=user)
        ).distinct()
    
    def perform_update(self, serializer):
        # 获取原始任务数据
        old_task = self.get_object()
        old_values = {
            'status': old_task.status,
            'priority': old_task.priority,
            'progress': old_task.progress,
            'assignee': old_task.assignee.username if old_task.assignee else None,
            'due_date': old_task.due_date.isoformat() if old_task.due_date else None
        }
        
        # 保存更新
        task = serializer.save()
        
        # 处理文件上传（如果有的话）
        files = self.request.FILES.getlist('files')
        if files:
            for uploaded_file in files:
                TaskAttachment.objects.create(
                    task=task,
                    file=uploaded_file,
                    filename=uploaded_file.name,
                    uploaded_by=self.request.user,
                    file_size=uploaded_file.size
                )
            
            # 记录文件上传日志
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='attachment_uploaded',
                description=f'编辑任务时上传了 {len(files)} 个文件',
                new_value={
                    'file_count': len(files),
                    'filenames': [f.name for f in files]
                },
                request=self.request
            )
        
        # 检查哪些字段发生了变更并记录日志
        new_values = {
            'status': task.status,
            'priority': task.priority,
            'progress': task.progress,
            'assignee': task.assignee.username if task.assignee else None,
            'due_date': task.due_date.isoformat() if task.due_date else None
        }
        
        # 状态变更
        if old_values['status'] != new_values['status']:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='status_changed',
                description=f'状态从 "{old_values["status"]}" 变更为 "{new_values["status"]}"',
                old_value={'status': old_values['status']},
                new_value={'status': new_values['status']},
                request=self.request
            )
        
        # 优先级变更
        if old_values['priority'] != new_values['priority']:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='priority_changed',
                description=f'优先级从 "{old_values["priority"]}" 变更为 "{new_values["priority"]}"',
                old_value={'priority': old_values['priority']},
                new_value={'priority': new_values['priority']},
                request=self.request
            )
        
        # 进度更新
        if old_values['progress'] != new_values['progress']:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='progress_updated',
                description=f'进度从 {old_values["progress"]}% 更新为 {new_values["progress"]}%',
                old_value={'progress': old_values['progress']},
                new_value={'progress': new_values['progress']},
                request=self.request
            )
        
        # 任务分配变更
        if old_values['assignee'] != new_values['assignee']:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='assigned',
                description=f'任务重新分配：从 "{old_values["assignee"] or "未分配"}" 变更为 "{new_values["assignee"] or "未分配"}"',
                old_value={'assignee': old_values['assignee']},
                new_value={'assignee': new_values['assignee']},
                request=self.request
            )
        
        # 截止日期变更
        if old_values['due_date'] != new_values['due_date']:
            TaskLog.log_action(
                task=task,
                user=self.request.user,
                action='deadline_changed',
                description=f'截止日期从 "{old_values["due_date"] or "未设置"}" 变更为 "{new_values["due_date"] or "未设置"}"',
                old_value={'due_date': old_values['due_date']},
                new_value={'due_date': new_values['due_date']},
                request=self.request
            )

    def perform_destroy(self, instance):
        # 检查权限：任务创建者或项目负责人可以删除任务
        user = self.request.user
        task = instance
        
        is_creator = task.creator == user
        is_project_owner = task.project and task.project.owner == user
        
        if not (is_creator or is_project_owner):
            raise PermissionDenied('只有任务创建者或项目负责人可以删除任务')
        
        # 记录删除日志
        TaskLog.log_action(
            task=task,
            user=user,
            action='deleted',
            description=f'删除了任务：{task.title}',
            old_value={
                'task_id': task.id,
                'title': task.title,
                'status': task.status,
                'creator': task.creator.username,
                'assignee': task.assignee.username if task.assignee else None
            },
            request=self.request
        )
        
        # 删除任务（这会级联删除相关的附件、评论等）
        instance.delete()

class TaskCommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCommentCreateSerializer
        return TaskCommentSerializer

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        return TaskComment.objects.filter(task_id=task_id).order_by('created_at')

    def perform_create(self, serializer):
        task_id = self.kwargs['task_id']
        task = Task.objects.get(id=task_id)
        comment = serializer.save(author=self.request.user, task=task)
        
        # 记录评论日志
        TaskLog.log_action(
            task=task,
            user=self.request.user,
            action='comment_added',
            description=f'添加了评论：{comment.content[:50]}{"..." if len(comment.content) > 50 else ""}',
            new_value={'comment_id': comment.id, 'content': comment.content},
            request=self.request
        )

class TaskAttachmentListView(generics.ListAPIView):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        return TaskAttachment.objects.filter(task_id=task_id).order_by('-uploaded_at')


class TaskAttachmentUploadView(generics.CreateAPIView):
    serializer_class = TaskAttachmentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        task_id = self.kwargs['task_id']
        task = Task.objects.get(id=task_id)
        
        # 检查权限
        user = self.request.user
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            raise PermissionDenied('无权限上传此任务的附件')
        
        # 如果没有提供filename，使用上传文件的原始名称
        filename = serializer.validated_data.get('filename')
        file = serializer.validated_data.get('file')
        if not filename and file:
            filename = file.name
        
        attachment = serializer.save(
            task=task,
            uploaded_by=user,
            filename=filename or file.name
        )
        
        # 记录上传日志
        TaskLog.log_action(
            task=task,
            user=user,
            action='attachment_uploaded',
            description=f'上传了附件：{attachment.filename} ({attachment.file_size_display})',
            new_value={
                'attachment_id': attachment.id,
                'filename': attachment.filename,
                'file_type': attachment.file_type,
                'file_size': attachment.file_size
            },
            request=self.request
        )


class TaskAttachmentDeleteView(generics.DestroyAPIView):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.all()

    def perform_destroy(self, instance):
        # 检查权限
        user = self.request.user
        task = instance.task
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            raise PermissionDenied('无权限删除此附件')
        
        # 记录删除日志
        TaskLog.log_action(
            task=task,
            user=user,
            action='attachment_deleted',
            description=f'删除了附件：{instance.filename}',
            old_value={
                'attachment_id': instance.id,
                'filename': instance.filename,
                'file_type': instance.file_type,
                'file_size': instance.file_size
            },
            request=self.request
        )
        
        instance.delete()


class TaskLogListView(generics.ListAPIView):
    serializer_class = TaskLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        # 检查任务权限
        user = self.request.user
        task = Task.objects.filter(
            Q(id=task_id) & (Q(creator=user) | Q(assignee=user) | Q(project__members=user))
        ).first()
        if not task:
            return TaskLog.objects.none()
        
        return TaskLog.objects.filter(task_id=task_id).order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_summary_with_logs(request, task_id):
    """获取任务详情及其日志摘要"""
    try:
        user = request.user
        task = Task.objects.filter(
            Q(id=task_id) & (Q(creator=user) | Q(assignee=user) | Q(project__members=user))
        ).first()
        
        if not task:
            return Response({'error': '任务不存在或无权限访问'}, status=status.HTTP_404_NOT_FOUND)
        
        # 获取任务基本信息
        task_data = TaskSerializer(task).data
        
        # 获取最近的日志记录
        recent_logs = TaskLog.objects.filter(task=task).order_by('-created_at')[:10]
        logs_data = TaskLogSerializer(recent_logs, many=True).data
        
        # 获取附件信息
        attachments = TaskAttachment.objects.filter(task=task).order_by('-uploaded_at')
        attachments_data = TaskAttachmentSerializer(attachments, many=True).data
        
        # 统计信息
        stats = {
            'total_logs': TaskLog.objects.filter(task=task).count(),
            'total_attachments': attachments.count(),
            'total_comments': TaskComment.objects.filter(task=task).count(),
            'total_evaluations': TaskEvaluation.objects.filter(task=task).count()
        }
        
        return Response({
            'task': task_data,
            'recent_logs': logs_data,
            'attachments': attachments_data,
            'stats': stats
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def update_task_status(request, task_id):
    """更新任务状态"""
    try:
        task = Task.objects.get(id=task_id)
        
        # 检查权限
        user = request.user
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            return Response({'error': '无权限修改此任务'}, status=status.HTTP_403_FORBIDDEN)
        
        new_status = request.data.get('status')
        if new_status not in ['pending', 'in_progress', 'completed', 'cancelled']:
            return Response({'error': '无效的状态'}, status=status.HTTP_400_BAD_REQUEST)
        
        task.status = new_status
        if new_status == 'completed':
            from django.utils import timezone
            task.completion_date = timezone.now()
        task.save()
        
        return Response({
            'message': f"任务状态已更新为 {task.get_status_display()}",
            'status': task.status
        })
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def my_task_summary(request):
    """获取用户任务摘要"""
    user = request.user
    
    # 我创建的任务统计
    created_tasks = Task.objects.filter(creator=user)
    created_stats = {
        'total': created_tasks.count(),
        'pending': created_tasks.filter(status='pending').count(),
        'in_progress': created_tasks.filter(status='in_progress').count(),
        'completed': created_tasks.filter(status='completed').count(),
    }
    
    # 分配给我的任务统计
    assigned_tasks = Task.objects.filter(assignee=user)
    assigned_stats = {
        'total': assigned_tasks.count(),
        'pending': assigned_tasks.filter(status='pending').count(),
        'in_progress': assigned_tasks.filter(status='in_progress').count(),
        'completed': assigned_tasks.filter(status='completed').count(),
    }
    
    # 最近的任务
    recent_tasks = Task.objects.filter(
        Q(creator=user) | Q(assignee=user)
    ).distinct().order_by('-updated_at')[:5]
    
    return Response({
        'created_tasks': created_stats,
        'assigned_tasks': assigned_stats,
        'recent_tasks': TaskSerializer(recent_tasks, many=True).data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def evaluate_task(request, task_id):
    """评估任务分数"""
    try:
        task = Task.objects.get(id=task_id)
        user = request.user
        
        # 检查权限：只有任务参与者、创建者或项目成员可以评估
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            return Response({'error': '无权限评估此任务'}, status=status.HTTP_403_FORBIDDEN)
        
        # 检查任务是否已完成
        if task.status != 'completed':
            return Response({'error': '只能评估已完成的任务'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查是否已经评估过
        if TaskEvaluation.objects.filter(task=task, evaluator=user).exists():
            return Response({'error': '您已经评估过此任务'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        
        # 创建评估记录
        evaluation = TaskEvaluation.objects.create(
            task=task,
            evaluator=user,
            evaluated_user=task.assignee or task.creator,
            score_type=data.get('score_type', 'function'),
            total_score=Decimal(str(data.get('total_score', 0))),
            criteria_scores=data.get('criteria_scores', {}),
            comment=data.get('comment', ''),
            improvement_suggestions=data.get('improvement_suggestions', ''),
            work_weight=Decimal(str(data.get('work_weight', 1.0))),
            evaluation_mode=data.get('evaluation_mode', 'peer')
        )
        
        # 更新任务的功分
        update_task_function_score(task)
        
        return Response({
            'message': '任务评估成功',
            'evaluation': TaskEvaluationSerializer(evaluation).data
        })
        
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def update_task_function_score(task):
    """更新任务的功分"""
    # 获取该任务的所有评估
    evaluations = TaskEvaluation.objects.filter(task=task, score_type='function')
    
    if not evaluations.exists():
        return
    
    # 计算平均功分
    avg_score = evaluations.aggregate(avg_score=Avg('total_score'))['avg_score']
    avg_weight = evaluations.aggregate(avg_weight=Avg('work_weight'))['avg_weight']
    
    if avg_score:
        # 功分 = 平均评分 × 平均工作权重 × 时效系数
        function_score = Decimal(str(avg_score)) * Decimal(str(avg_weight or 1.0)) * task.time_coefficient
        task.function_score = function_score
        task.save()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_evaluation_list(request, task_id):
    """获取任务评估列表"""
    try:
        task = Task.objects.get(id=task_id)
        user = request.user
        
        # 检查权限
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            return Response({'error': '无权限查看此任务评估'}, status=status.HTTP_403_FORBIDDEN)
        
        evaluations = TaskEvaluation.objects.filter(task=task).order_by('-created_at')
        serializer = TaskEvaluationSerializer(evaluations, many=True)
        
        return Response(serializer.data)
        
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_task_score_summary(request):
    """获取用户任务分数汇总"""
    user = request.user
    
    # 获取用户参与的所有已完成任务
    completed_tasks = Task.objects.filter(
        Q(creator=user) | Q(assignee=user),
        status='completed'
    ).distinct()
    
    # 统计总分数
    total_system_score = sum(task.system_score or 0 for task in completed_tasks)
    total_function_score = sum(task.function_score or 0 for task in completed_tasks)
    total_score = total_system_score + total_function_score
    
    # 按项目统计
    project_scores = {}
    for task in completed_tasks:
        if task.project:
            project_id = task.project.id
            project_name = task.project.name
            if project_id not in project_scores:
                project_scores[project_id] = {
                    'project_name': project_name,
                    'system_score': 0,
                    'function_score': 0,
                    'task_count': 0
                }
            project_scores[project_id]['system_score'] += task.system_score or 0
            project_scores[project_id]['function_score'] += task.function_score or 0
            project_scores[project_id]['task_count'] += 1
    
    # 最近的评估
    recent_evaluations = TaskEvaluation.objects.filter(
        evaluated_user=user
    ).order_by('-created_at')[:5]
    
    return Response({
        'total_scores': {
            'system_score': float(total_system_score),
            'function_score': float(total_function_score),
            'total_score': float(total_score),
            'task_count': completed_tasks.count()
        },
        'project_scores': list(project_scores.values()),
        'recent_evaluations': TaskEvaluationSerializer(recent_evaluations, many=True).data
    })

class TaskEvaluationSessionListCreateView(generics.ListCreateAPIView):
    """任务评估会话列表和创建"""
    serializer_class = TaskEvaluationSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project')
        
        # 用户可以看到自己参与的或创建的评估会话
        queryset = TaskEvaluationSession.objects.filter(
            Q(created_by=user) | Q(participants=user) | Q(project__members=user)
        ).distinct()
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        # 检查项目权限
        project = serializer.validated_data.get('project')
        user = self.request.user
        
        # 只有项目成员才能创建评估会话
        if not project.members.filter(id=user.id).exists():
            raise serializers.ValidationError('只有项目成员才能创建评估会话')
        
        serializer.save(created_by=user)

class TaskEvaluationSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """任务评估会话详情"""
    serializer_class = TaskEvaluationSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return TaskEvaluationSession.objects.filter(
            Q(created_by=user) | Q(participants=user) | Q(project__members=user)
        ).distinct()

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_batch_task_evaluation(request, session_id):
    """批量提交任务评估"""
    try:
        session = TaskEvaluationSession.objects.get(id=session_id)
        user = request.user
        
        # 检查权限：只有参与者可以提交评估
        if not session.participants.filter(id=user.id).exists():
            return Response({'error': '您不是此评估会话的参与者'}, status=status.HTTP_403_FORBIDDEN)
        
        # 检查会话状态
        if session.status != 'active':
            return Response({'error': '评估会话已结束'}, status=status.HTTP_400_BAD_REQUEST)
        
        evaluations_data = request.data.get('evaluations', [])
        
        if not evaluations_data:
            return Response({'error': '没有提供评估数据'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_evaluations = []
        
        for eval_data in evaluations_data:
            task_id = eval_data.get('task_id')
            evaluated_user_id = eval_data.get('evaluated_user')
            
            try:
                task = Task.objects.get(id=task_id)
                evaluated_user = task.assignee or task.creator
                
                # 检查是否已经评估过
                if TaskEvaluation.objects.filter(task=task, evaluator=user, evaluated_user=evaluated_user).exists():
                    continue  # 跳过已评估的
                
                # 创建评估记录
                evaluation = TaskEvaluation.objects.create(
                    task=task,
                    evaluator=user,
                    evaluated_user=evaluated_user,
                    score_type='function',
                    total_score=Decimal(str(eval_data.get('score', 0))),
                    criteria_scores=eval_data.get('criteria_scores', {}),
                    comment=eval_data.get('comment', ''),
                    improvement_suggestions=eval_data.get('improvement_suggestions', ''),
                    work_weight=Decimal(str(eval_data.get('work_weight', 1.0))),
                    evaluation_mode='peer'
                )
                created_evaluations.append(evaluation)
                
            except Task.DoesNotExist:
                continue  # 跳过不存在的任务
        
        # 检查评估会话是否可以完成
        if session.can_complete():
            session.complete_session()
        
        return Response({
            'message': f'成功提交 {len(created_evaluations)} 项评估',
            'evaluations': TaskEvaluationSerializer(created_evaluations, many=True).data,
            'session_status': session.status,
            'completion_percentage': session.completion_percentage
        })
        
    except TaskEvaluationSession.DoesNotExist:
        return Response({'error': '评估会话不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_evaluation_session(request, session_id):
    """手动完成评估会话"""
    try:
        session = TaskEvaluationSession.objects.get(id=session_id)
        user = request.user
        
        # 检查权限：只有创建者可以手动完成会话
        if session.created_by != user:
            return Response({'error': '只有创建者可以完成评估会话'}, status=status.HTTP_403_FORBIDDEN)
        
        # 检查会话状态
        if session.status != 'active':
            return Response({'error': '评估会话已结束'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session.complete_session()
            return Response({
                'message': '评估会话已完成',
                'session': TaskEvaluationSessionSerializer(session).data
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    except TaskEvaluationSession.DoesNotExist:
        return Response({'error': '评估会话不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def evaluation_session_summary(request, session_id):
    """获取评估会话摘要"""
    try:
        session = TaskEvaluationSession.objects.get(id=session_id)
        user = request.user
        
        # 检查权限
        if not (session.created_by == user or 
                session.participants.filter(id=user.id).exists() or
                session.project.members.filter(id=user.id).exists()):
            return Response({'error': '无权限查看此评估会话'}, status=status.HTTP_403_FORBIDDEN)
        
        summary = session.get_evaluation_summary()
        
        return Response({
            'session': TaskEvaluationSessionSerializer(session).data,
            'summary': summary
        })
        
    except TaskEvaluationSession.DoesNotExist:
        return Response({'error': '评估会话不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_hall_list(request):
    """获取任务大厅中的可领取任务列表"""
    try:
        # 获取所有标记为可领取且未分配的任务
        available_tasks = Task.objects.filter(
            is_available_for_claim=True,
            assignee__isnull=True,
            status='pending'
        ).select_related('project', 'creator').order_by('-created_at')
        
        # 分页处理
        page = request.GET.get('page', 1)
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # 最大100条每页
        
        # 手动分页
        start_idx = (int(page) - 1) * page_size
        end_idx = start_idx + page_size
        tasks_page = available_tasks[start_idx:end_idx]
        
        serializer = TaskSerializer(tasks_page, many=True)
        
        return Response({
            'tasks': serializer.data,
            'total': available_tasks.count(),
            'page': int(page),
            'page_size': page_size,
            'has_next': end_idx < available_tasks.count(),
            'has_prev': int(page) > 1
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def claim_task(request, task_id):
    """领取任务"""
    try:
        task = Task.objects.get(id=task_id)
        
        # 检查任务是否可以被领取
        if not task.is_available_for_claim:
            return Response({'error': '该任务不可被领取'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查任务是否已经被分配
        if task.assignee is not None:
            return Response({'error': '该任务已被其他人领取'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查任务状态
        if task.status != 'pending':
            return Response({'error': '只能领取待处理状态的任务'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户是否是项目成员
        user = request.user
        if not task.project.members.filter(id=user.id).exists():
            return Response({'error': '只有项目成员才能领取任务'}, status=status.HTTP_403_FORBIDDEN)
        
        # 分配任务给用户
        task.assignee = user
        task.status = 'in_progress'
        task.save()
        
        # 记录日志
        TaskLog.log_action(
            task=task,
            user=user,
            action='assigned',
            description=f'用户 {user.username} 领取了任务',
            new_value={'assignee': user.username, 'assignee_id': user.id, 'status': 'in_progress'},
            request=request
        )
        
        return Response({
            'message': '成功领取任务',
            'task': TaskSerializer(task).data
        })
        
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 用户任务日志相关视图
class TaskUserLogListCreateView(generics.ListCreateAPIView):
    """用户任务日志列表和创建"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskUserLogCreateSerializer
        return TaskUserLogSerializer
    
    def get_queryset(self):
        task_id = self.kwargs['task_id']
        # 检查任务权限
        user = self.request.user
        task = Task.objects.filter(
            Q(id=task_id) & (Q(creator=user) | Q(assignee=user) | Q(project__members=user))
        ).first()
        if not task:
            return TaskUserLog.objects.none()
        
        return TaskUserLog.objects.filter(task_id=task_id).order_by('-created_at')
    
    def perform_create(self, serializer):
        task_id = self.kwargs['task_id']
        try:
            task = Task.objects.get(id=task_id)
            user = self.request.user
            
            # 检查权限
            if not (task.creator == user or task.assignee == user or 
                    (task.project and task.project.members.filter(id=user.id).exists())):
                raise PermissionDenied('无权限为此任务添加日志')
            
            # 保存日志
            user_log = serializer.save(task=task, user=user)
            
            # 如果日志包含进度更新，同时更新任务进度
            if user_log.progress is not None:
                old_progress = task.progress
                task.progress = user_log.progress
                task.save()
                
                # 记录系统日志
                TaskLog.log_action(
                    task=task,
                    user=user,
                    action='progress_updated',
                    description=f'通过用户日志更新进度：{user_log.title}',
                    old_value={'progress': old_progress},
                    new_value={'progress': user_log.progress},
                    request=self.request
                )
            
        except Task.DoesNotExist:
            raise PermissionDenied('任务不存在')


class TaskUserLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    """用户任务日志详情"""
    serializer_class = TaskUserLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TaskUserLog.objects.all()
    
    def perform_update(self, serializer):
        user_log = self.get_object()
        user = self.request.user
        
        # 检查权限：只有创建者或任务负责人可以编辑
        if not (user_log.user == user or user_log.task.assignee == user or user_log.task.creator == user):
            raise PermissionDenied('无权限编辑此日志')
        
        # 保存更新
        updated_log = serializer.save()
        
        # 如果进度发生变化，更新任务进度
        if 'progress' in serializer.validated_data and updated_log.progress is not None:
            old_progress = updated_log.task.progress
            if old_progress != updated_log.progress:
                updated_log.task.progress = updated_log.progress
                updated_log.task.save()
    
    def perform_destroy(self, instance):
        user = self.request.user
        
        # 检查权限：只有创建者可以删除
        if instance.user != user:
            raise PermissionDenied('只能删除自己创建的日志')
        
        instance.delete()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_task_user_log_attachment(request, log_id):
    """为用户任务日志上传附件"""
    try:
        user_log = TaskUserLog.objects.get(id=log_id)
        user = request.user
        
        # 检查权限
        if not (user_log.user == user or user_log.task.assignee == user or user_log.task.creator == user):
            return Response({'error': '无权限为此日志上传附件'}, status=status.HTTP_403_FORBIDDEN)
        
        if 'file' not in request.FILES:
            return Response({'error': '没有上传文件'}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        filename = request.data.get('filename', uploaded_file.name)
        
        # 创建附件
        attachment = TaskUserLogAttachment.objects.create(
            log=user_log,
            file=uploaded_file,
            filename=filename,
            file_size=uploaded_file.size
        )
        
        serializer = TaskUserLogAttachmentSerializer(attachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except TaskUserLog.DoesNotExist:
        return Response({'error': '日志不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Merit Calculation Views ====================

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def task_merit_calculation(request, task_id):
    """任务功分计算管理"""
    try:
        task = Task.objects.get(id=task_id)
        user = request.user
        
        # 检查权限：只有项目成员可以访问
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            return Response({'error': '无权限访问此任务的功分计算'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'GET':
            # 获取功分计算记录
            try:
                calculation = TaskTeamMeritCalculation.objects.get(task=task)
                participant_results = TaskTeamMeritResult.objects.filter(calculation=calculation)
                
                return Response({
                    'calculation': {
                        'id': calculation.id,
                        'method': calculation.calculation_method,
                        'participant_count': calculation.participant_count,
                        'total_contribution': float(calculation.total_contribution),
                        'is_finalized': calculation.is_finalized,
                        'calculated_at': calculation.calculated_at,
                        'summary': calculation.calculation_summary
                    },
                    'participants': [
                        {
                            'user_id': result.participant.id,
                            'username': result.participant.username,
                            'contribution_value': float(result.contribution_value),
                            'merit_points': float(result.merit_points),
                            'merit_percentage': result.merit_percentage,
                            'weight_factor': float(result.weight_factor) if result.weight_factor else None,
                            'adjustment_factor': float(result.adjustment_factor) if result.adjustment_factor else None
                        }
                        for result in participant_results
                    ]
                })
            except TaskTeamMeritCalculation.DoesNotExist:
                return Response({'calculation': None, 'participants': []})
        
        elif request.method == 'POST':
            # 创建或更新功分计算
            participants_data = request.data.get('participants', [])
            
            if not participants_data:
                return Response({'error': '参与者数据不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建或获取计算记录
            calculation, created = TaskTeamMeritCalculation.objects.get_or_create(
                task=task,
                defaults={
                    'calculation_method': 'single',
                    'participant_count': len(participants_data),
                    'total_contribution': 0
                }
            )
            
            # 更新或创建参与者结果
            for participant_data in participants_data:
                user_id = participant_data.get('user_id')
                contribution_value = participant_data.get('contribution_value', 0)
                
                if not user_id:
                    continue
                
                TaskTeamMeritResult.objects.update_or_create(
                    calculation=calculation,
                    participant_id=user_id,
                    defaults={'contribution_value': Decimal(str(contribution_value))}
                )
            
            # 重新计算功分
            calculation.calculate_merit_points()
            
            return Response({'message': '功分计算已更新', 'calculation_id': calculation.id})
            
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def finalize_merit_calculation(request, task_id):
    """确定功分计算结果"""
    try:
        task = Task.objects.get(id=task_id)
        user = request.user
        
        # 检查权限：只有项目创建者或任务创建者可以确定功分
        if not (task.creator == user or 
                (task.project and task.project.owner == user)):
            return Response({'error': '无权限确定此任务的功分计算'}, status=status.HTTP_403_FORBIDDEN)
        
        calculation = TaskTeamMeritCalculation.objects.get(task=task)
        
        if calculation.is_finalized:
            return Response({'error': '功分计算已经确定，不能重复操作'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确定计算结果
        calculation.finalize_calculation()
        
        # 记录操作日志
        TaskLog.log_action(
            task=task,
            user=user,
            action='evaluation_added',
            description=f'确定了功分计算结果，参与者数量：{calculation.participant_count}',
            new_value={
                'calculation_method': calculation.calculation_method,
                'participant_count': calculation.participant_count,
                'total_contribution': float(calculation.total_contribution)
            },
            request=request
        )
        
        return Response({'message': '功分计算已确定'})
        
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    except TaskTeamMeritCalculation.DoesNotExist:
        return Response({'error': '功分计算记录不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def task_contribution_records(request, task_id):
    """任务贡献记录管理"""
    try:
        task = Task.objects.get(id=task_id)
        user = request.user
        
        # 检查权限
        if not (task.creator == user or task.assignee == user or 
                (task.project and task.project.members.filter(id=user.id).exists())):
            return Response({'error': '无权限访问此任务的贡献记录'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'GET':
            # 获取贡献记录
            records = TaskContributionRecord.objects.filter(task=task).order_by('-created_at')
            
            # 按贡献者分组
            contributions_by_user = {}
            for record in records:
                user_id = record.contributor.id
                if user_id not in contributions_by_user:
                    contributions_by_user[user_id] = {
                        'user_id': user_id,
                        'username': record.contributor.username,
                        'total_weighted_score': 0,
                        'contributions': []
                    }
                
                contributions_by_user[user_id]['contributions'].append({
                    'id': record.id,
                    'contribution_type': record.contribution_type,
                    'contribution_type_display': record.get_contribution_type_display(),
                    'score': float(record.score),
                    'weight': float(record.weight),
                    'weighted_score': float(record.weighted_score),
                    'description': record.description,
                    'evidence': record.evidence,
                    'recorder': record.recorder.username,
                    'created_at': record.created_at
                })
                
                contributions_by_user[user_id]['total_weighted_score'] += float(record.weighted_score)
            
            return Response({
                'contributors': list(contributions_by_user.values()),
                'contribution_types': TaskContributionRecord.CONTRIBUTION_TYPE_CHOICES
            })
        
        elif request.method == 'POST':
            # 添加贡献记录
            contributor_id = request.data.get('contributor_id')
            contribution_type = request.data.get('contribution_type')
            score = request.data.get('score')
            weight = request.data.get('weight', 1.0)
            description = request.data.get('description', '')
            evidence = request.data.get('evidence', '')
            
            if not contributor_id or not contribution_type or score is None:
                return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查contributor是否存在且是项目成员
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                contributor = User.objects.get(id=contributor_id)
                if task.project and not task.project.members.filter(id=contributor_id).exists():
                    return Response({'error': '被评估者不是项目成员'}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({'error': '被评估者不存在'}, status=status.HTTP_404_NOT_FOUND)
            
            # 创建贡献记录
            record = TaskContributionRecord.objects.create(
                task=task,
                contributor=contributor,
                recorder=user,
                contribution_type=contribution_type,
                score=Decimal(str(score)),
                weight=Decimal(str(weight)),
                description=description,
                evidence=evidence
            )
            
            return Response({
                'message': '贡献记录已添加',
                'record': {
                    'id': record.id,
                    'contribution_type': record.contribution_type,
                    'score': float(record.score),
                    'weight': float(record.weight),
                    'weighted_score': float(record.weighted_score)
                }
            })
            
    except Task.DoesNotExist:
        return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_merit_summary(request):
    """用户功分汇总"""
    user = request.user
    
    try:
        # 获取用户的所有功分结果
        merit_results = TaskTeamMeritResult.objects.filter(
            participant=user,
            calculation__is_finalized=True
        ).select_related('calculation__task__project')
        
        # 按项目分组统计
        project_stats = {}
        total_merit = 0
        total_tasks = 0
        
        for result in merit_results:
            task = result.calculation.task
            project = task.project
            project_id = project.id if project else 0
            project_name = project.name if project else '未分类'
            
            if project_id not in project_stats:
                project_stats[project_id] = {
                    'project_id': project_id,
                    'project_name': project_name,
                    'total_merit': 0,
                    'task_count': 0,
                    'tasks': []
                }
            
            project_stats[project_id]['total_merit'] += float(result.merit_points)
            project_stats[project_id]['task_count'] += 1
            project_stats[project_id]['tasks'].append({
                'task_id': task.id,
                'task_title': task.title,
                'merit_points': float(result.merit_points),
                'merit_percentage': result.merit_percentage,
                'calculation_method': result.calculation.get_calculation_method_display(),
                'calculated_at': result.calculation.calculated_at
            })
            
            total_merit += float(result.merit_points)
            total_tasks += 1
        
        # 获取最近的贡献记录
        recent_contributions = TaskContributionRecord.objects.filter(
            contributor=user
        ).select_related('task', 'recorder').order_by('-created_at')[:10]
        
        return Response({
            'summary': {
                'total_merit_points': total_merit,
                'total_tasks': total_tasks,
                'average_merit_per_task': total_merit / total_tasks if total_tasks > 0 else 0,
                'project_count': len(project_stats)
            },
            'project_stats': list(project_stats.values()),
            'recent_contributions': [
                {
                    'id': record.id,
                    'task_title': record.task.title,
                    'contribution_type': record.get_contribution_type_display(),
                    'score': float(record.score),
                    'weighted_score': float(record.weighted_score),
                    'recorder': record.recorder.username,
                    'created_at': record.created_at
                }
                for record in recent_contributions
            ]
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)