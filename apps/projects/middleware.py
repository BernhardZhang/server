from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import json
import re

User = get_user_model()

class ProjectActivityLoggerMiddleware(MiddlewareMixin):
    """
    项目活动日志中间件
    自动记录所有项目相关的操作
    """
    
    def process_response(self, request, response):
        # 只记录已认证用户的POST、PUT、DELETE操作
        if (not hasattr(request, 'user') or 
            not request.user.is_authenticated or 
            request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']):
            return response
        
        # 只记录项目相关的API请求
        if not self._is_project_related(request.path):
            return response
        
        # 只记录成功的响应
        if not (200 <= response.status_code < 300):
            return response
        
        try:
            self._log_activity(request, response)
        except Exception as e:
            # 记录日志失败不应该影响主要功能
            print(f"Failed to log project activity: {e}")
        
        return response
    
    def _is_project_related(self, path):
        """检查路径是否与项目相关"""
        project_patterns = [
            r'/api/projects/',
            r'/api/tasks/',
            r'/api/members/',
            r'/api/ratings/',
            r'/api/evaluations/',
            r'/api/points/',
            r'/api/voting/',
        ]
        
        for pattern in project_patterns:
            if re.search(pattern, path):
                return True
        return False
    
    def _log_activity(self, request, response):
        """记录项目活动"""
        from .models import ProjectLog, Project
        
        # 解析请求路径获取项目ID
        project_id = self._extract_project_id(request.path)
        if not project_id:
            return
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return
        
        # 确定日志类型和操作功能
        log_type, action_function = self._determine_log_type(request, response)
        if not log_type:
            return
        
        # 创建日志标题
        title = f"{request.user.username} {action_function}"
        
        # 创建详细描述
        description = self._create_description(request, response)
        
        # 获取IP地址和用户代理
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # 获取相关对象信息
        related_objects = self._get_related_objects(request, response)
        
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
            **related_objects
        )
    
    def _extract_project_id(self, path):
        """从路径中提取项目ID"""
        # 匹配 /api/projects/{id}/ 或 /api/projects/{id}/
        match = re.search(r'/api/projects/(\d+)/?', path)
        if match:
            return int(match.group(1))
        
        # 匹配其他项目相关的路径
        # 例如：/api/tasks/?project_id=123
        if 'project_id=' in path:
            match = re.search(r'project_id=(\d+)', path)
            if match:
                return int(match.group(1))
        
        return None
    
    def _determine_log_type(self, request, response):
        """确定日志类型和操作功能"""
        path = request.path
        method = request.method
        
        # 项目相关操作
        if '/api/projects/' in path:
            if method == 'POST':
                return 'project_created', '创建了项目'
            elif method in ['PUT', 'PATCH']:
                return 'project_updated', '更新了项目信息'
            elif method == 'DELETE':
                return 'project_deleted', '删除了项目'
        
        # 任务相关操作
        elif '/api/tasks/' in path:
            if method == 'POST':
                return 'task_created', '创建了任务'
            elif method in ['PUT', 'PATCH']:
                return 'task_updated', '更新了任务'
            elif method == 'DELETE':
                return 'task_deleted', '删除了任务'
        
        # 成员管理操作
        elif '/api/members/' in path:
            if method == 'POST':
                return 'member_invited', '邀请了成员'
            elif method in ['PUT', 'PATCH']:
                return 'member_role_changed', '变更了成员角色'
            elif method == 'DELETE':
                return 'member_removed', '移除了成员'
        
        # 评分相关操作
        elif '/api/ratings/' in path or '/api/evaluations/' in path:
            if method == 'POST':
                return 'rating_created', '创建了评分'
            elif method in ['PUT', 'PATCH']:
                return 'rating_completed', '完成了评分'
        
        # 积分相关操作
        elif '/api/points/' in path:
            if method == 'POST':
                return 'points_awarded', '奖励了积分'
        
        # 投票相关操作
        elif '/api/voting/' in path:
            if method == 'POST':
                return 'vote_participated', '参与了投票'
        
        return None, None
    
    def _create_description(self, request, response):
        """创建详细描述"""
        descriptions = []
        
        # 从响应数据中提取信息
        if hasattr(response, 'data') and isinstance(response.data, dict):
            data = response.data
            
            # 任务相关信息
            if 'title' in data:
                descriptions.append(f"任务：{data['title']}")
            
            # 用户相关信息
            if 'user_name' in data:
                descriptions.append(f"用户：{data['user_name']}")
            elif 'username' in data:
                descriptions.append(f"用户：{data['username']}")
            
            # 状态变更
            if 'status' in data:
                descriptions.append(f"状态：{data['status']}")
            
            # 角色变更
            if 'role' in data:
                descriptions.append(f"角色：{data['role']}")
        
        return '；'.join(descriptions) if descriptions else ''
    
    def _get_related_objects(self, request, response):
        """获取相关对象信息"""
        related_objects = {}
        
        if hasattr(response, 'data') and isinstance(response.data, dict):
            data = response.data
            
            # 相关任务
            if 'id' in data and '/api/tasks/' in request.path:
                related_objects['related_task_id'] = data['id']
            
            # 相关用户
            if 'user' in data:
                related_objects['related_user_id'] = data['user']
            elif 'assignee' in data:
                related_objects['related_user_id'] = data['assignee']
            
            # 变更内容
            if 'changes' in data:
                related_objects['changes'] = data['changes']
            
            # 元数据
            metadata = {}
            for key in ['priority', 'status', 'role', 'progress']:
                if key in data:
                    metadata[key] = data[key]
            
            if metadata:
                related_objects['metadata'] = metadata
        
        return related_objects
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
