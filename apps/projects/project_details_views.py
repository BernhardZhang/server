from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Project, ProjectMembership
from .services import ProjectDetailsService
import logging

logger = logging.getLogger(__name__)

class ProjectViewSet(viewsets.ModelViewSet):
    """项目视图集（现有的项目ViewSet基础上添加详情导出功能）"""

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def export_details(self, request, pk=None):
        """导出项目详情为markdown格式"""
        try:
            project = get_object_or_404(Project, pk=pk)

            # 检查用户权限：项目成员才能查看详情
            if not request.user.is_staff:
                membership = ProjectMembership.objects.filter(
                    project=project,
                    user=request.user,
                    is_active=True
                ).first()

                if not membership and project.owner != request.user:
                    return Response(
                        {'error': '您没有权限查看此项目的详细信息'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # 收集项目详情数据
            logger.info(f"开始收集项目 {project.id} 的详情数据")
            project_details = ProjectDetailsService.collect_project_details(project.id)

            if not project_details:
                return Response(
                    {'error': '项目详情数据收集失败'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 生成结构化报告（便于AI理解）
            structured_report = ProjectDetailsService.generate_structured_report(project_details)

            logger.info(f"成功生成项目 {project.id} 的结构化详情报告")

            return Response({
                'success': True,
                'project_id': project.id,
                'project_name': project.name,
                'structured_content': structured_report,  # 使用结构化数据而非markdown
                'data_summary': {
                    'members_count': len(project_details.get('members', [])),
                    'tasks_count': project_details.get('tasks', {}).get('total_count', 0),
                    'revenue_count': project_details.get('revenue', {}).get('revenue_count', 0),
                    'logs_count': project_details.get('logs', {}).get('recent_logs_count', 0),
                    'merit_points': project_details.get('merit', {}).get('total_merit_points', 0),
                    'voting_count': project_details.get('voting', {}).get('voting_count', 0),
                    'rating_sessions_count': project_details.get('voting', {}).get('rating_sessions_count', 0),
                    'recruitment_count': project_details.get('recruitment', {}).get('recruitment_count', 0),
                    'applications_count': project_details.get('applications', {}).get('total_applications', 0),  # 新增
                },
                'generated_at': project_details.get('generated_at')
            })

        except Exception as e:
            logger.error(f"导出项目详情失败: {str(e)}")
            return Response(
                {'error': f'导出项目详情失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def raw_details(self, request, pk=None):
        """获取项目详情原始数据（JSON格式）"""
        try:
            project = get_object_or_404(Project, pk=pk)

            # 检查用户权限
            if not request.user.is_staff:
                membership = ProjectMembership.objects.filter(
                    project=project,
                    user=request.user,
                    is_active=True
                ).first()

                if not membership and project.owner != request.user:
                    return Response(
                        {'error': '您没有权限查看此项目的详细信息'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # 收集项目详情数据
            project_details = ProjectDetailsService.collect_project_details(project.id)

            if not project_details:
                return Response(
                    {'error': '项目详情数据收集失败'},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                'success': True,
                'data': project_details
            })

        except Exception as e:
            logger.error(f"获取项目详情原始数据失败: {str(e)}")
            return Response(
                {'error': f'获取项目详情失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )