from rest_framework import permissions

class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：允许认证用户进行任何操作，未认证用户只能查看
    """
    def has_permission(self, request, view):
        # 允许安全方法（GET, HEAD, OPTIONS）给所有用户
        if request.method in permissions.SAFE_METHODS:
            return True
        # 其他方法需要认证
        return request.user and request.user.is_authenticated

class IsProjectMemberOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：允许项目成员进行任何操作，未认证用户只能查看
    """
    def has_permission(self, request, view):
        # 允许安全方法（GET, HEAD, OPTIONS）给所有用户
        if request.method in permissions.SAFE_METHODS:
            return True
        # 其他方法需要认证
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # 允许安全方法（GET, HEAD, OPTIONS）给所有用户
        if request.method in permissions.SAFE_METHODS:
            return True
        # 其他方法需要是项目成员
        if hasattr(obj, 'project'):
            project = obj.project
        else:
            project = obj
        return (request.user and request.user.is_authenticated and 
                (request.user == project.owner or 
                 project.projectmembership_set.filter(user=request.user).exists()))