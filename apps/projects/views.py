from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from decimal import Decimal
from .models import (
    Project, ProjectMembership, ProjectLog,
    MemberRecruitment, MemberApplication, ProjectRevenue, RevenueDistribution
)
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectLogSerializer,
    ProjectMembershipSerializer,
    MemberRecruitmentSerializer, MemberRecruitmentCreateSerializer,
    MemberApplicationSerializer, MemberApplicationCreateSerializer,
    ProjectRevenueSerializer, ProjectRevenueCreateSerializer,
    RevenueDistributionSerializer
)
from .permissions import IsAuthenticatedOrReadOnly, IsProjectMemberOrReadOnly
from .project_points_view import project_points

User = get_user_model()

class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.filter(is_active=True).select_related('owner').prefetch_related('projectmembership_set__user')
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer

    def perform_create(self, serializer):
        project = serializer.save()
        # 确保数据被正确加载并返回
        project.refresh_from_db()
        return project

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectMemberOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_update(self, serializer):
        print(f"DEBUG: Updating project with data: {serializer.validated_data}")
        project = self.get_object()
        user = self.request.user

        # 获取要更新的字段
        update_fields = set(serializer.validated_data.keys())

        # 如果只更新 is_public 字段，放宽权限检查
        if update_fields == {'is_public'}:
            # 项目所有者和项目成员都可以更新公开状态
            if user == project.owner or project.members.filter(id=user.id).exists():
                serializer.save()
                return

        # 对于其他字段的更新，需要更严格的权限检查
        if user != project.owner:
            # 检查用户是否是项目管理员
            try:
                membership = ProjectMembership.objects.get(user=user, project=project)
                if membership.role not in ['owner', 'admin']:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('只有项目负责人或管理员可以修改项目')
            except ProjectMembership.DoesNotExist:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('只有项目负责人或管理员可以修改项目')

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """重写destroy方法以支持软删除并返回适当响应"""
        instance = self.get_object()

        # 检查权限
        if request.user != instance.owner:
            return Response({'error': '只有项目负责人可以删除项目'}, status=status.HTTP_403_FORBIDDEN)

        # 软删除：设置is_active=False而不是真正删除
        instance.is_active = False
        instance.save()

        # 记录删除日志
        try:
            ProjectLog.create_log(
                project=instance,
                log_type='project_deleted',
                user=request.user,
                title=f'删除了项目 "{instance.name}"',
                description='项目已被标记为删除状态'
            )
        except Exception as e:
            print(f"Failed to create delete log: {e}")

        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_project(request):
    """加入公开项目"""
    project_id = request.data.get('project_id')
    message = request.data.get('message', '')

    if not project_id:
        return Response({'error': '项目ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        project = Project.objects.get(id=project_id, is_public=True, is_active=True)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在或不是公开项目'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 检查是否已经是成员
    if ProjectMembership.objects.filter(project=project, user=user, is_active=True).exists():
        return Response({'error': '您已经是该项目的成员'}, status=status.HTTP_400_BAD_REQUEST)

    # 创建成员关系
    membership = ProjectMembership.objects.create(
        project=project,
        user=user,
        role='member'
    )

    return Response({'message': '成功加入项目', 'membership_id': membership.id})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_by_code(request):
    """通过邀请码加入项目"""
    try:
        join_code = request.data.get('join_code')
        if not join_code:
            return Response({'error': '邀请码不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找项目
        try:
            project = Project.objects.get(invite_code=join_code, is_active=True)
        except Project.DoesNotExist:
            return Response({'error': '邀请码无效或项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 检查邀请码是否有效
        if not project.is_invite_code_valid():
            return Response({'error': '邀请码已过期或已禁用'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查用户是否已经是项目成员
        if project.members.filter(id=request.user.id).exists():
            return Response({'error': '您已经是该项目成员'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建项目成员关系
        membership, created = ProjectMembership.objects.get_or_create(
            user=request.user,
            project=project,
            defaults={'contribution_percentage': 0.00}
        )

        if created:
            # 记录项目日志
            ProjectLog.create_log(
                project=project,
                log_type='member_joined',
                user=request.user,
                title=f'{request.user.username} 通过邀请码加入了项目',
                description=f'用户通过邀请码 {join_code} 加入项目'
            )
            return Response({
                'message': '成功加入项目',
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description
                }
            })
        else:
            return Response({'error': '加入项目失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({'error': f'加入项目失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_invite_code(request, project_id):
    """生成项目邀请码"""
    try:
        project = Project.objects.get(id=project_id, is_active=True)

        # 检查权限：只有项目负责人和管理员可以生成邀请码
        if project.owner != request.user:
            # 检查是否是项目管理员
            try:
                membership = ProjectMembership.objects.get(user=request.user, project=project)
                if membership.role not in ['owner', 'admin']:
                    return Response({'error': '只有项目负责人和管理员可以生成邀请码'}, status=status.HTTP_403_FORBIDDEN)
            except ProjectMembership.DoesNotExist:
                return Response({'error': '只有项目负责人和管理员可以生成邀请码'}, status=status.HTTP_403_FORBIDDEN)

        # 生成邀请码
        invite_code = project.generate_invite_code()

        # 记录项目日志
        ProjectLog.create_log(
            project=project,
            log_type='invite_code_generated',
            user=request.user,
            title=f'生成了新的邀请码',
            description=f'邀请码: {invite_code}，有效期至: {project.invite_code_expires_at.strftime("%Y-%m-%d %H:%M:%S")}'
        )

        return Response({
            'invite_code': invite_code,
            'expires_at': project.invite_code_expires_at,
            'message': '邀请码生成成功'
        })

    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'生成邀请码失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def leave_project(request):
    """离开项目"""
    project_id = request.data.get('project_id')

    if not project_id:
        return Response({'error': '项目ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 项目负责人不能离开项目
    if project.owner == user:
        return Response({'error': '项目负责人不能离开项目'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = ProjectMembership.objects.get(project=project, user=user, is_active=True)
        membership.delete()
        return Response({'message': '成功离开项目'})
    except ProjectMembership.DoesNotExist:
        return Response({'error': '您不是该项目的成员'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_member_role(request):
    """更新成员角色"""
    membership_id = request.data.get('membership_id')
    new_role = request.data.get('role')

    if not membership_id or not new_role:
        return Response({'error': '成员ID和角色不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = ProjectMembership.objects.get(id=membership_id)
    except ProjectMembership.DoesNotExist:
        return Response({'error': '成员关系不存在'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    project = membership.project

    # 只有项目负责人或管理员可以更新成员角色
    if user != project.owner:
        try:
            user_membership = ProjectMembership.objects.get(user=user, project=project)
            if user_membership.role not in ['owner', 'admin']:
                return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)
        except ProjectMembership.DoesNotExist:
            return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)

    # 不能将项目负责人的角色改为其他角色
    if membership.user == project.owner and new_role != 'owner':
        return Response({'error': '不能更改项目负责人的角色'}, status=status.HTTP_400_BAD_REQUEST)

    old_role = membership.role
    membership.role = new_role
    membership.save()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='member_role_changed',
        user=user,
        title=f'更新了 {membership.user.username} 的角色',
        description=f'角色从 {old_role} 改为 {new_role}',
        related_user=membership.user
    )

    return Response({'message': '角色更新成功'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def remove_member(request):
    """移除项目成员"""
    membership_id = request.data.get('membership_id')

    if not membership_id:
        return Response({'error': '成员ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = ProjectMembership.objects.get(id=membership_id)
    except ProjectMembership.DoesNotExist:
        return Response({'error': '成员关系不存在'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    project = membership.project

    # 只有项目负责人或管理员可以移除成员
    if user != project.owner:
        try:
            user_membership = ProjectMembership.objects.get(user=user, project=project)
            if user_membership.role not in ['owner', 'admin']:
                return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)
        except ProjectMembership.DoesNotExist:
            return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)

    # 不能移除项目负责人
    if membership.user == project.owner:
        return Response({'error': '不能移除项目负责人'}, status=status.HTTP_400_BAD_REQUEST)

    removed_user = membership.user
    membership.delete()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='member_removed',
        user=user,
        title=f'移除了成员 {removed_user.username}',
        description=f'从项目中移除了成员 {removed_user.username}',
        related_user=removed_user
    )

    return Response({'message': f'成功移除成员 {removed_user.username}'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_member_admin(request, project_id, user_id):
    """设置成员为管理员（REST风格API，使用user_id）"""
    try:
        project = Project.objects.get(id=project_id, is_active=True)
    except Project.DoesNotExist:
        return Response({'error': f'项目ID {project_id} 不存在'}, status=status.HTTP_404_NOT_FOUND)

    try:
        membership = ProjectMembership.objects.get(user_id=user_id, project_id=project_id)
    except ProjectMembership.DoesNotExist:
        return Response({
            'error': f'成员关系不存在',
            'debug_info': f'项目ID: {project_id}, 用户ID: {user_id}',
            'suggestion': '该用户不是此项目的成员'
        }, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 只有项目负责人或管理员可以设置管理员
    if user != project.owner:
        try:
            user_membership = ProjectMembership.objects.get(user=user, project=project)
            if user_membership.role not in ['owner', 'admin']:
                return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)
        except ProjectMembership.DoesNotExist:
            return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)

    # 不能将项目负责人的角色改为其他角色（如果需要的话可以启用）
    # if membership.user == project.owner:
    #     return Response({'error': '不能更改项目负责人的角色'}, status=status.HTTP_400_BAD_REQUEST)

    old_role = membership.role
    new_role = 'admin'

    if old_role == new_role:
        return Response({'message': f'{membership.user.username} 已经是管理员了'})

    # 检查是否已有管理员（单管理员限制）
    existing_admin = ProjectMembership.objects.filter(
        project=project,
        role='admin',
        is_active=True
    ).exclude(id=membership.id).first()

    if existing_admin:
        return Response({
            'error': '该项目已有管理员',
            'current_admin': {
                'username': existing_admin.user.username,
                'user_id': existing_admin.user.id
            },
            'suggestion': '每个项目只能有一个管理员，请先移除当前管理员'
        }, status=status.HTTP_400_BAD_REQUEST)

    membership.role = new_role
    membership.save()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='member_role_changed',
        user=user,
        title=f'设置 {membership.user.username} 为管理员',
        description=f'角色从 {old_role} 改为 {new_role}',
        related_user=membership.user
    )

    # 返回更新后的成员信息
    from .serializers import ProjectMembershipSerializer
    updated_membership = ProjectMembershipSerializer(membership).data

    return Response({
        'message': f'成功设置 {membership.user.username} 为管理员',
        'updated_membership': updated_membership,
        'project_id': project_id,
        'member_count': project.member_count  # 添加最新成员数量
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def remove_member_admin(request, project_id, user_id):
    """取消成员管理员角色（REST风格API，使用user_id）"""
    try:
        project = Project.objects.get(id=project_id, is_active=True)
    except Project.DoesNotExist:
        return Response({'error': f'项目ID {project_id} 不存在'}, status=status.HTTP_404_NOT_FOUND)

    try:
        membership = ProjectMembership.objects.get(user_id=user_id, project_id=project_id)
    except ProjectMembership.DoesNotExist:
        return Response({
            'error': f'成员关系不存在',
            'debug_info': f'项目ID: {project_id}, 用户ID: {user_id}',
            'suggestion': '该用户不是此项目的成员'
        }, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 只有项目负责人或当前用户自己可以取消管理员
    if user != project.owner and user != membership.user:
        return Response({'error': '只有项目负责人或管理员自己可以取消管理员角色'}, status=status.HTTP_403_FORBIDDEN)

    old_role = membership.role
    new_role = 'member'

    if old_role == new_role:
        return Response({'message': f'{membership.user.username} 已经是普通成员了'})

    if old_role != 'admin':
        return Response({'error': f'{membership.user.username} 不是管理员'}, status=status.HTTP_400_BAD_REQUEST)

    membership.role = new_role
    membership.save()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='member_role_changed',
        user=user,
        title=f'取消了 {membership.user.username} 的管理员角色',
        description=f'角色从 {old_role} 改为 {new_role}',
        related_user=membership.user
    )

    # 返回更新后的成员信息
    from .serializers import ProjectMembershipSerializer
    updated_membership = ProjectMembershipSerializer(membership).data

    return Response({
        'message': f'成功取消 {membership.user.username} 的管理员角色',
        'updated_membership': updated_membership,
        'project_id': project_id,
        'member_count': project.member_count
    })

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_project_member(request, project_id, user_id):
    """移除项目成员（REST风格API，使用user_id）"""
    try:
        project = Project.objects.get(id=project_id, is_active=True)
    except Project.DoesNotExist:
        return Response({'error': f'项目ID {project_id} 不存在'}, status=status.HTTP_404_NOT_FOUND)

    try:
        membership = ProjectMembership.objects.get(user_id=user_id, project_id=project_id)
    except ProjectMembership.DoesNotExist:
        return Response({
            'error': f'成员关系不存在',
            'debug_info': f'项目ID: {project_id}, 用户ID: {user_id}',
            'suggestion': '该用户不是此项目的成员'
        }, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # 只有项目负责人或管理员可以移除成员
    if user != project.owner:
        try:
            user_membership = ProjectMembership.objects.get(user=user, project=project)
            if user_membership.role not in ['owner', 'admin']:
                return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)
        except ProjectMembership.DoesNotExist:
            return Response({'error': '权限不足'}, status=status.HTTP_403_FORBIDDEN)

    # 不能移除项目负责人
    if membership.user == project.owner:
        return Response({'error': '不能移除项目负责人'}, status=status.HTTP_400_BAD_REQUEST)

    # 不能移除自己
    if membership.user == user:
        return Response({'error': '不能移除自己，请使用离开项目功能'}, status=status.HTTP_400_BAD_REQUEST)

    removed_user = membership.user
    removed_user_info = {
        'user_id': removed_user.id,
        'username': removed_user.username
    }
    membership.delete()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='member_removed',
        user=user,
        title=f'移除了成员 {removed_user.username}',
        description=f'从项目中移除了成员 {removed_user.username}',
        related_user=removed_user
    )

    return Response({
        'message': f'成功移除成员 {removed_user.username}',
        'removed_member': removed_user_info,
        'project_id': project_id,
        'member_count': project.member_count  # 添加最新成员数量
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_projects(request):
    """获取当前用户的所有项目"""
    user = request.user
    # 获取用户拥有或参与的项目
    projects = Project.objects.filter(
        Q(owner=user) | Q(members=user),
        is_active=True
    ).distinct().select_related('owner').prefetch_related('projectmembership_set__user')

    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_contribution(request):
    """更新成员贡献度"""
    membership_id = request.data.get('membership_id')
    contribution_percentage = request.data.get('contribution_percentage')

    if membership_id is None or contribution_percentage is None:
        return Response({'error': '成员ID和贡献度不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        membership = ProjectMembership.objects.get(id=membership_id)
    except ProjectMembership.DoesNotExist:
        return Response({'error': '成员关系不存在'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    project = membership.project

    # 只有项目负责人可以更新贡献度
    if user != project.owner:
        return Response({'error': '只有项目负责人可以更新贡献度'}, status=status.HTTP_403_FORBIDDEN)

    try:
        contribution_percentage = float(contribution_percentage)
        if contribution_percentage < 0 or contribution_percentage > 100:
            return Response({'error': '贡献度必须在0-100之间'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return Response({'error': '贡献度必须是数字'}, status=status.HTTP_400_BAD_REQUEST)

    old_percentage = membership.contribution_percentage
    membership.contribution_percentage = contribution_percentage
    membership.save()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='contribution_updated',
        user=user,
        title=f'更新了 {membership.user.username} 的贡献度',
        description=f'贡献度从 {old_percentage}% 改为 {contribution_percentage}%',
        related_user=membership.user
    )

    return Response({'message': '贡献度更新成功'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def public_projects(request):
    """获取公开项目列表"""
    projects = Project.objects.filter(
        is_public=True,
        is_active=True
    ).select_related('owner').prefetch_related('projectmembership_set__user')

    # 搜索功能
    search = request.GET.get('search')
    if search:
        projects = projects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )

    # 项目类型过滤
    project_type = request.GET.get('project_type')
    if project_type:
        projects = projects.filter(project_type=project_type)

    # 状态过滤
    status_filter = request.GET.get('status')
    if status_filter:
        projects = projects.filter(status=status_filter)

    # 排序
    ordering = request.GET.get('ordering', '-created_at')
    projects = projects.order_by(ordering)

    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def distribute_revenue(request):
    """分配项目收益"""
    revenue_id = request.data.get('revenue_id')

    if not revenue_id:
        return Response({'error': '收益记录ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        revenue = ProjectRevenue.objects.get(id=revenue_id)
    except ProjectRevenue.DoesNotExist:
        return Response({'error': '收益记录不存在'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    project = revenue.project

    # 只有项目负责人可以分配收益
    if user != project.owner:
        return Response({'error': '只有项目负责人可以分配收益'}, status=status.HTTP_403_FORBIDDEN)

    if revenue.is_distributed:
        return Response({'error': '该收益已经分配过了'}, status=status.HTTP_400_BAD_REQUEST)

    # 获取所有活跃成员
    active_members = ProjectMembership.objects.filter(
        project=project,
        is_active=True
    ).select_related('user')

    if not active_members.exists():
        return Response({'error': '项目没有活跃成员'}, status=status.HTTP_400_BAD_REQUEST)

    # 计算总贡献度
    total_contribution = sum(member.contribution_percentage for member in active_members)

    if total_contribution == 0:
        return Response({'error': '总贡献度为0，无法分配收益'}, status=status.HTTP_400_BAD_REQUEST)

    # 为每个成员创建分配记录
    distributions = []
    total_distributed = Decimal('0')

    for membership in active_members:
        # 计算分配金额
        distribution_amount = (revenue.net_amount * Decimal(str(membership.contribution_percentage))) / Decimal(str(total_contribution))

        distribution = RevenueDistribution.objects.create(
            revenue=revenue,
            member=membership.user,
            membership=membership,
            amount=distribution_amount,
            equity_percentage_at_time=membership.contribution_percentage
        )
        distributions.append(distribution)
        total_distributed += distribution_amount

    # 更新收益记录
    revenue.is_distributed = True
    revenue.distribution_date = timezone.now()
    revenue.save()

    # 记录日志
    ProjectLog.create_log(
        project=project,
        log_type='revenue_distributed',
        user=user,
        title=f'分配了收益：{revenue.description}',
        description=f'总金额 {revenue.net_amount}，分配给 {len(distributions)} 位成员'
    )

    return Response({
        'message': '收益分配成功',
        'distributed_amount': total_distributed,
        'distributions': RevenueDistributionSerializer(distributions, many=True).data
    })

# ViewSets for CRUD operations
class ProjectMembershipViewSet(ModelViewSet):
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 只返回用户参与的项目的成员信息
        return ProjectMembership.objects.filter(
            project__in=Project.objects.filter(
                Q(owner=user) | Q(members=user)
            )
        ).select_related('user', 'project')

class ProjectLogViewSet(ModelViewSet):
    serializer_class = ProjectLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']  # 只允许读取

    def get_queryset(self):
        user = self.request.user
        # 只返回用户参与的项目的日志
        return ProjectLog.objects.filter(
            project__in=Project.objects.filter(
                Q(owner=user) | Q(members=user)
            )
        ).select_related('user', 'project', 'related_user').order_by('-created_at')

class MemberRecruitmentViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'work_type', 'project']
    ordering_fields = ['created_at', 'deadline']
    ordering = ['-created_at']

    def get_queryset(self):
        return MemberRecruitment.objects.all().select_related('project', 'created_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return MemberRecruitmentCreateSerializer
        return MemberRecruitmentSerializer

class MemberApplicationViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'recruitment']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # 用户可以看到自己的申请和自己项目招募的申请
        return MemberApplication.objects.filter(
            Q(applicant=user) | Q(recruitment__created_by=user)
        ).select_related('recruitment', 'applicant', 'reviewed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return MemberApplicationCreateSerializer
        return MemberApplicationSerializer

class ProjectRevenueViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['revenue_type', 'is_distributed', 'project']
    ordering_fields = ['revenue_date', 'created_at']
    ordering = ['-revenue_date']

    def get_queryset(self):
        user = self.request.user
        # 只返回用户参与的项目的收益记录
        return ProjectRevenue.objects.filter(
            project__in=Project.objects.filter(
                Q(owner=user) | Q(members=user)
            )
        ).select_related('project', 'recorded_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectRevenueCreateSerializer
        return ProjectRevenueSerializer

class RevenueDistributionViewSet(ModelViewSet):
    serializer_class = RevenueDistributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch']  # 只允许读取和更新支付状态

    def get_queryset(self):
        user = self.request.user
        # 用户可以看到自己的分配记录和自己项目的所有分配记录
        return RevenueDistribution.objects.filter(
            Q(member=user) | Q(revenue__project__owner=user)
        ).select_related('revenue', 'member', 'membership')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_logs(request, project_id):
    """获取项目日志"""
    try:
        project = Project.objects.get(id=project_id)

        # 检查用户是否有权限查看此项目的日志
        if not (request.user == project.owner or
                project.projectmembership_set.filter(user=request.user).exists()):
            return Response(
                {'error': '您没有权限查看此项目的日志'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # 获取项目日志
        logs = ProjectLog.objects.filter(project=project).select_related(
            'user', 'related_user'
        ).order_by('-created_at')

        # 分页
        from django.core.paginator import Paginator
        paginator = Paginator(logs, page_size)
        page_obj = paginator.get_page(page)

        # 序列化数据
        serializer = ProjectLogSerializer(page_obj.object_list, many=True)

        return Response({
            'results': serializer.data,
            'has_more': page_obj.has_next(),
            'total': paginator.count,
            'page': page,
            'page_size': page_size
        })

    except Project.DoesNotExist:
        return Response(
            {'error': '项目不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_project_log(request, project_id):
    """创建项目日志"""
    try:
        project = Project.objects.get(id=project_id)

        # 检查用户是否有权限创建此项目的日志
        if not (request.user == project.owner or
                project.projectmembership_set.filter(user=request.user).exists()):
            return Response(
                {'error': '您没有权限创建此项目的日志'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 创建日志
        log_data = request.data.copy()
        log_data['project'] = project.id
        log_data['user'] = request.user.id

        serializer = ProjectLogSerializer(data=log_data)
        if serializer.is_valid():
            log = serializer.save()
            return Response(
                ProjectLogSerializer(log).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

    except Project.DoesNotExist:
        return Response(
            {'error': '项目不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )