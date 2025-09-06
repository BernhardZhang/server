from functools import wraps
from django.http import HttpRequest
from django.contrib.auth import get_user_model
from .models import ProjectLog
import json

User = get_user_model()

def log_project_activity(log_type, action_function, get_project_id=None, get_related_objects=None):
    """
    装饰器：自动记录项目操作日志
    
    Args:
        log_type: 日志类型
        action_function: 操作功能描述
        get_project_id: 函数，从request或response中获取项目ID
        get_related_objects: 函数，获取相关对象信息
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 执行原始视图函数
            response = view_func(request, *args, **kwargs)
            
            # 记录日志
            try:
                if isinstance(request, HttpRequest) and hasattr(request, 'user') and request.user.is_authenticated:
                    # 获取项目ID
                    project_id = None
                    if get_project_id:
                        project_id = get_project_id(request, response, *args, **kwargs)
                    elif 'project_id' in kwargs:
                        project_id = kwargs['project_id']
                    elif 'pk' in kwargs:
                        project_id = kwargs['pk']
                    
                    if project_id:
                        from .models import Project
                        try:
                            project = Project.objects.get(id=project_id)
                            
                            # 获取相关对象信息
                            related_objects = {}
                            if get_related_objects:
                                related_objects = get_related_objects(request, response, *args, **kwargs)
                            
                            # 创建日志标题
                            title = f"{request.user.username} {action_function}"
                            
                            # 创建详细描述
                            description_parts = []
                            if related_objects.get('task_title'):
                                description_parts.append(f"任务：{related_objects['task_title']}")
                            if related_objects.get('user_name'):
                                description_parts.append(f"用户：{related_objects['user_name']}")
                            if related_objects.get('changes'):
                                description_parts.append(f"变更：{json.dumps(related_objects['changes'], ensure_ascii=False)}")
                            
                            description = '；'.join(description_parts) if description_parts else ''
                            
                            # 获取IP地址和用户代理
                            ip_address = get_client_ip(request)
                            user_agent = request.META.get('HTTP_USER_AGENT', '')
                            
                            # 创建日志
                            ProjectLog.create_log(
                                project=project,
                                log_type=log_type,
                                user=request.user,
                                title=title,
                                description=description,
                                action_method=request.method,
                                action_function=action_function,
                                ip_address=ip_address,
                                user_agent=user_agent,
                                related_task_id=related_objects.get('task_id'),
                                related_user_id=related_objects.get('user_id'),
                                changes=related_objects.get('changes', {}),
                                metadata=related_objects.get('metadata', {})
                            )
                        except Project.DoesNotExist:
                            pass
            except Exception as e:
                # 记录日志失败不应该影响主要功能
                print(f"Failed to create project log: {e}")
            
            return response
        return wrapper
    return decorator

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# 预定义的常用装饰器
def log_task_creation(view_func):
    """记录任务创建日志"""
    def get_project_id(request, response, *args, **kwargs):
        if hasattr(response, 'data') and 'project' in response.data:
            return response.data['project']
        return kwargs.get('project_id')
    
    def get_related_objects(request, response, *args, **kwargs):
        if hasattr(response, 'data'):
            return {
                'task_id': response.data.get('id'),
                'task_title': response.data.get('title'),
                'metadata': {
                    'priority': response.data.get('priority'),
                    'status': response.data.get('status'),
                    'assignee': response.data.get('assignee')
                }
            }
        return {}
    
    return log_project_activity('task_created', '创建了任务', get_project_id, get_related_objects)(view_func)

def log_task_update(view_func):
    """记录任务更新日志"""
    def get_project_id(request, response, *args, **kwargs):
        if hasattr(response, 'data') and 'project' in response.data:
            return response.data['project']
        return kwargs.get('project_id')
    
    def get_related_objects(request, response, *args, **kwargs):
        if hasattr(response, 'data'):
            return {
                'task_id': response.data.get('id'),
                'task_title': response.data.get('title'),
                'changes': response.data.get('changes', {}),
                'metadata': {
                    'updated_fields': list(response.data.get('changes', {}).keys())
                }
            }
        return {}
    
    return log_project_activity('task_updated', '更新了任务', get_project_id, get_related_objects)(view_func)

def log_member_management(view_func):
    """记录成员管理日志"""
    def get_project_id(request, response, *args, **kwargs):
        return kwargs.get('project_id')
    
    def get_related_objects(request, response, *args, **kwargs):
        if hasattr(response, 'data'):
            return {
                'user_id': response.data.get('user'),
                'user_name': response.data.get('user_name'),
                'metadata': {
                    'role': response.data.get('role'),
                    'action': 'invite' if 'invite' in request.path else 'remove'
                }
            }
        return {}
    
    return log_project_activity('member_invited', '管理了项目成员', get_project_id, get_related_objects)(view_func)

def log_project_update(view_func):
    """记录项目更新日志"""
    def get_project_id(request, response, *args, **kwargs):
        return kwargs.get('pk') or kwargs.get('project_id')
    
    def get_related_objects(request, response, *args, **kwargs):
        if hasattr(response, 'data'):
            return {
                'changes': response.data.get('changes', {}),
                'metadata': {
                    'updated_fields': list(response.data.get('changes', {}).keys())
                }
            }
        return {}
    
    return log_project_activity('project_updated', '更新了项目信息', get_project_id, get_related_objects)(view_func)
