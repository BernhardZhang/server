from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def project_points(request):
    """获取项目积分/功分计算数据"""
    try:
        project_id = request.GET.get('project')
        if not project_id:
            return Response(
                {'error': '缺少项目ID参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 导入merit app的模型和计算逻辑
        from apps.merit.models import ProjectMeritCalculation, MeritCalculationResult

        try:
            # 查找项目的功分计算
            calculation = ProjectMeritCalculation.objects.filter(
                project_id=project_id,
                status='completed'
            ).order_by('-created_at').first()

            if not calculation:
                return Response({
                    'message': '该项目暂无功分计算数据',
                    'results': []
                })

            # 获取计算结果
            results = MeritCalculationResult.objects.filter(
                calculation=calculation
            ).order_by('rank')

            # 序列化结果数据
            result_data = []
            for result in results:
                result_data.append({
                    'user_id': result.user_id,
                    'user_name': result.user.username if result.user else 'Unknown',
                    'rank': result.rank,
                    'total_system_score': float(result.total_system_score),
                    'function_score': float(result.function_score),
                    'final_score': float(result.final_score),
                    'average_peer_review_score': float(result.average_peer_review_score),
                    'individual_points': float(result.individual_points),
                    'total_team_points': float(result.total_team_points),
                    'total_peer_reviews_received': result.total_peer_reviews_received,
                })

            return Response({
                'calculation_name': calculation.name,
                'calculation_id': calculation.id,
                'total_project_value': float(calculation.total_project_value),
                'status': calculation.status,
                'results': result_data
            })

        except Exception as e:
            return Response(
                {'error': f'获取功分计算数据失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )