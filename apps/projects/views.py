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

    return Response({'message': f'成功移除成员 {removed_user.username}'})

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