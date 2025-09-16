from rest_framework import serializers
from .models import Task, TaskComment, TaskAttachment, TaskEvaluation, TaskEvaluationSession, TaskLog, TaskUserLog, TaskUserLogAttachment, TaskAssignment

class TaskSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    comments_count = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    # 添加参与成员字段支持
    participating_members = serializers.SerializerMethodField(read_only=True)
    participating_members_input = serializers.JSONField(required=False, write_only=True)
    task_percentage = serializers.IntegerField(required=False, write_only=True)

    def get_participating_members(self, obj):
        """获取参与成员列表"""
        try:
            assignments = TaskAssignment.objects.filter(task=obj)
            return [
                {
                    'user': assignment.user.id,
                    'user_name': assignment.user.username,
                    'coefficient': float(assignment.role_weight),
                    'role_weight': float(assignment.role_weight)
                }
                for assignment in assignments
            ]
        except Exception:
            # 如果查询失败，返回空列表
            return []

    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'creator', 'creator_name', 'assignee', 'assignee_name',
                 'project', 'project_name', 'status', 'priority', 'start_date', 'due_date', 'completion_date',
                 'completed_at', 'progress', 'estimated_hours', 'actual_hours', 'system_score',
                 'function_score', 'time_coefficient', 'weight_coefficient', 'tags', 'tag_list', 'category', 'is_overdue',
                 'is_available_for_claim', 'comments_count', 'attachments', 'created_at', 'updated_at',
                 'participating_members', 'participating_members_input', 'task_percentage')
        read_only_fields = ('creator', 'project')  # 这些字段只读，不允许通过API修改

    def update(self, instance, validated_data):
        # 处理参与成员数据
        participating_members = validated_data.pop('participating_members_input', None)
        # 移除不在模型中的字段，避免验证错误
        validated_data.pop('task_percentage', None)

        # 添加调试日志
        print(f"DEBUG: participating_members data: {participating_members}")

        # 调用父类的update方法
        task = super().update(instance, validated_data)

        # 处理参与成员
        if participating_members is not None:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()

                # 删除现有的任务分配
                TaskAssignment.objects.filter(task=task).delete()

                # 创建新的任务分配
                for member_data in participating_members:
                    try:
                        user_id = member_data.get('user')
                        coefficient = member_data.get('coefficient', 1.0)

                        if user_id:
                            user = User.objects.get(id=user_id)
                            TaskAssignment.objects.create(
                                task=task,
                                user=user,
                                role_weight=coefficient
                            )
                    except (User.DoesNotExist, ValueError, KeyError):
                        # 忽略无效的用户数据
                        continue
            except Exception:
                # 如果处理失败，忽略
                pass

        return task

    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_tag_list(self, obj):
        return obj.tag_list
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_attachments(self, obj):
        return TaskAttachmentSerializer(obj.attachments.all(), many=True).data

class TaskCreateSerializer(serializers.ModelSerializer):
    participating_members_input = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = Task
        fields = ('title', 'description', 'assignee', 'weight_coefficient', 'project', 'priority', 'start_date',
                 'due_date', 'estimated_hours', 'progress', 'tags', 'category', 'is_available_for_claim',
                 'participating_members_input')

    def create(self, validated_data):
        # 处理参与成员数据
        participating_members = validated_data.pop('participating_members_input', [])

        # 创建任务
        task = super().create(validated_data)

        # 处理参与成员
        if participating_members:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()

                # 创建任务分配
                for member_data in participating_members:
                    try:
                        user_id = member_data.get('user')
                        coefficient = member_data.get('coefficient', 1.0)

                        if user_id:
                            user = User.objects.get(id=user_id)
                            TaskAssignment.objects.create(
                                task=task,
                                user=user,
                                role_weight=coefficient
                            )
                    except (User.DoesNotExist, ValueError, KeyError):
                        # 忽略无效的用户数据
                        continue
            except Exception:
                # 如果处理失败，忽略
                pass

        return task

class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = TaskComment
        fields = ('id', 'task', 'author', 'author_name', 'content', 'created_at')

class TaskCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ('content',)

class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_display = serializers.CharField(read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ('id', 'task', 'file', 'filename', 'file_type', 'file_type_display', 
                 'file_size', 'file_size_display', 'uploaded_by', 'uploaded_by_name', 
                 'description', 'uploaded_at')


class TaskAttachmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ('file', 'filename', 'description')
    
    def validate_file(self, value):
        # 文件大小限制：50MB
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("文件大小不能超过50MB")
        return value

class TaskEvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source='evaluator.username', read_only=True)
    evaluated_user_name = serializers.CharField(source='evaluated_user.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskEvaluation
        fields = ('id', 'task', 'task_title', 'evaluator', 'evaluator_name', 
                 'evaluated_user', 'evaluated_user_name', 'score_type', 'evaluation_mode',
                 'total_score', 'criteria_scores', 'comment', 'improvement_suggestions',
                 'work_weight', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class TaskEvaluationSessionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    participants_detail = serializers.SerializerMethodField(read_only=True)
    selected_tasks_detail = serializers.SerializerMethodField(read_only=True)
    completion_percentage = serializers.ReadOnlyField()
    evaluation_records = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TaskEvaluationSession
        fields = ('id', 'name', 'description', 'project', 'project_name', 'created_by', 'created_by_name',
                 'selected_tasks', 'selected_tasks_detail', 'participants', 'participants_detail', 
                 'status', 'criteria_config', 'start_time', 'end_time', 'deadline',
                 'completion_percentage', 'evaluation_records', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'completion_percentage', 'created_at', 'updated_at')
    
    def get_participants_detail(self, obj):
        return [{'id': p.id, 'username': p.username} for p in obj.participants.all()]
    
    def get_selected_tasks_detail(self, obj):
        tasks = []
        for task in obj.selected_tasks.all():
            tasks.append({
                'id': task.id,
                'title': task.title,
                'assignee': task.assignee.id if task.assignee else None,
                'assignee_name': task.assignee.username if task.assignee else None,
                'status': task.status,
                'system_score': float(task.system_score),
                'function_score': float(task.function_score)
            })
        return tasks
    
    def get_evaluation_records(self, obj):
        """获取评估记录摘要"""
        records = []
        for task in obj.selected_tasks.all():
            evaluations = TaskEvaluation.objects.filter(task=task)
            for evaluation in evaluations:
                records.append({
                    'task_id': task.id,
                    'task_title': task.title,
                    'evaluator': evaluation.evaluator.username,
                    'evaluated_user': evaluation.evaluated_user.username,
                    'total_score': float(evaluation.total_score),
                    'created_at': evaluation.created_at
                })
        return records


class TaskLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    change_summary = serializers.CharField(read_only=True)
    
    class Meta:
        model = TaskLog
        fields = ('id', 'task', 'user', 'user_name', 'action', 'action_display', 
                 'description', 'change_summary', 'old_value', 'new_value', 
                 'ip_address', 'created_at')
        read_only_fields = ('id', 'created_at')


class TaskUserLogAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskUserLogAttachment
        fields = ('id', 'file', 'filename', 'file_size', 'uploaded_at')
        read_only_fields = ('id', 'file_size', 'uploaded_at')


class TaskUserLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    attachments = TaskUserLogAttachmentSerializer(many=True, read_only=True)
    created_by = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskUserLog
        fields = ('id', 'task', 'user', 'user_name', 'log_type', 'log_type_display', 
                 'title', 'content', 'progress', 'attachments', 'created_by',
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def get_created_by(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'avatar': None  # 可以根据需要添加头像字段
        }


class TaskUserLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskUserLog
        fields = ('log_type', 'title', 'content', 'progress')