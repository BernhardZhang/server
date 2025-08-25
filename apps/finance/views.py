from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import FinancialReport, Transaction, ShareholderEquity
from .serializers import FinancialReportSerializer, FinancialReportCreateSerializer, TransactionSerializer, ShareholderEquitySerializer

class FinancialReportListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FinancialReportCreateSerializer
        return FinancialReportSerializer

    def get_queryset(self):
        user = self.request.user
        voting_round_id = self.request.query_params.get('voting_round')
        show_all = self.request.query_params.get('show_all', 'false').lower() == 'true'
        
        if show_all:
            # 显示所有已授权的报表
            queryset = FinancialReport.objects.filter(is_authorized=True)
        else:
            # 只显示用户自己的报表和参与项目的报表
            queryset = FinancialReport.objects.filter(
                Q(user=user) | Q(project__members=user)
            ).distinct()
        
        if voting_round_id:
            queryset = queryset.filter(voting_round_id=voting_round_id)
            
        return queryset.order_by('-created_at')

@api_view(['POST'])
def generate_financial_report(request):
    """根据真实交易数据自动生成财务报表"""
    from django.db.models import Sum, Q
    from decimal import Decimal
    from apps.voting.models import VotingRound, Vote, SelfEvaluation

    user_id = request.data.get('user_id')
    project_id = request.data.get('project_id')
    voting_round_id = request.data.get('voting_round_id')

    if not voting_round_id:
        return Response({'error': '必须指定投票轮次'}, status=status.HTTP_400_BAD_REQUEST)

    if not user_id and not project_id:
        return Response({'error': '必须指定用户或项目'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        voting_round = VotingRound.objects.get(id=voting_round_id)

        if user_id:
            # 个人财务报表
            from apps.users.models import User
            user = User.objects.get(id=user_id)

            # 计算收入 - 接收到的投票金额
            votes_received = Vote.objects.filter(
                target_user=user_id,
                voting_round=voting_round
                # is_paid=True  # 暂时去掉支付验证，接入微信支付后再启用
            )
            vote_revenue = votes_received.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # 计算收入 - 接收到的投资
            investments_received = SelfEvaluation.objects.filter(
                entity_type='user',
                entity_id=user_id,
                voting_round=voting_round,
                is_approved=True
            )
            investment_revenue = investments_received.aggregate(total=Sum('investment_amount'))['total'] or Decimal('0.00')

            total_revenue = vote_revenue + investment_revenue

            # 计算支出 - 投出的投票金额
            votes_cast = Vote.objects.filter(
                voter=user_id,
                voting_round=voting_round
                # is_paid=True  # 暂时去掉支付验证，接入微信支付后再启用
            )
            vote_costs = votes_cast.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # 计算支出 - 投出的投资金额
            investments_made = SelfEvaluation.objects.filter(
                investor=user_id,
                voting_round=voting_round,
                is_approved=True
            )
            investment_costs = investments_made.aggregate(total=Sum('investment_amount'))['total'] or Decimal('0.00')

            total_costs = vote_costs + investment_costs

            # 计算资产
            # 流动资产 = 用户余额（使用安全的属性获取）
            user_balance = Decimal('0.00')
            if hasattr(user, 'balance'):
                user_balance = user.balance or Decimal('0.00')
            elif hasattr(user, 'points'):
                user_balance = Decimal(str(user.points or 0))
            
            current_assets = user_balance

            # 固定资产 = 投资金额
            fixed_assets = investment_costs

            total_assets = current_assets + fixed_assets

            # 净资产 = 总资产 (假设没有负债)
            equity = total_assets

            # 现金流 = 收入 - 支出
            operating_cash_flow = total_revenue - total_costs

            # 收集调试信息
            debug_counts = {
                'votes_received_count': votes_received.count(),
                'investments_received_count': investments_received.count(),
                'votes_cast_count': votes_cast.count(),
                'investments_made_count': investments_made.count(),
                'user_has_balance': hasattr(user, 'balance'),
                'user_has_points': hasattr(user, 'points'),
                'voting_round_name': voting_round.name
            }

            # 创建或更新财务报表
            report, created = FinancialReport.objects.get_or_create(
                user_id=user_id,
                voting_round=voting_round,
                defaults={
                    'report_type': 'individual',
                    'data_source': 'calculated',
                    'total_assets': total_assets,
                    'current_assets': current_assets,
                    'fixed_assets': fixed_assets,
                    'equity': equity,
                    'revenue': total_revenue,
                    'costs': total_costs,
                    'operating_cash_flow': operating_cash_flow
                }
            )

            if not created:
                # 更新现有报表
                report.data_source = 'calculated'
                report.total_assets = total_assets
                report.current_assets = current_assets
                report.fixed_assets = fixed_assets
                report.equity = equity
                report.revenue = total_revenue
                report.costs = total_costs
                report.operating_cash_flow = operating_cash_flow
                report.save()

        elif project_id:
            # 项目财务报表
            from apps.projects.models import Project
            project = Project.objects.get(id=project_id)

            # 计算收入 - 项目接收到的投票
            project_votes = Vote.objects.filter(
                target_project=project_id,
                voting_round=voting_round
                # is_paid=True  # 暂时去掉支付验证，接入微信支付后再启用
            )
            vote_revenue = project_votes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            # 计算收入 - 项目接收到的投资
            project_investments = SelfEvaluation.objects.filter(
                entity_type='project',
                entity_id=project_id,
                voting_round=voting_round,
                is_approved=True
            )
            investment_revenue = project_investments.aggregate(total=Sum('investment_amount'))['total'] or Decimal('0.00')

            total_revenue = vote_revenue + investment_revenue

            # 项目支出通常较少，暂时设为0
            total_costs = Decimal('0.00')

            # 项目资产 = 收入
            total_assets = total_revenue
            current_assets = total_assets
            equity = total_assets

            operating_cash_flow = total_revenue - total_costs

            # 创建或更新项目财务报表
            report, created = FinancialReport.objects.get_or_create(
                project_id=project_id,
                voting_round=voting_round,
                defaults={
                    'report_type': 'project',
                    'data_source': 'calculated',
                    'total_assets': total_assets,
                    'current_assets': current_assets,
                    'equity': equity,
                    'revenue': total_revenue,
                    'costs': total_costs,
                    'operating_cash_flow': operating_cash_flow
                }
            )

            if not created:
                # 更新现有报表
                report.data_source = 'calculated'
                report.total_assets = total_assets
                report.current_assets = current_assets
                report.equity = equity
                report.revenue = total_revenue
                report.costs = total_costs
                report.operating_cash_flow = operating_cash_flow
                report.save()

        serializer = FinancialReportSerializer(report)
        return Response({
            'message': '财务报表已基于真实投票和投资数据生成',
            'report': serializer.data,
            'data_source': 'real_voting_data',
            'debug_info': {
                'vote_revenue': float(vote_revenue) if 'vote_revenue' in locals() else 0,
                'investment_revenue': float(investment_revenue) if 'investment_revenue' in locals() else 0,
                'vote_costs': float(vote_costs) if 'vote_costs' in locals() else 0,
                'investment_costs': float(investment_costs) if 'investment_costs' in locals() else 0,
                'debug_counts': debug_counts if 'debug_counts' in locals() else {},
                'current_user_id': user_id,
                'current_voting_round': voting_round_id
            }
        })

    except VotingRound.DoesNotExist:
        return Response({'error': '投票轮次不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'生成报表失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def authorize_report(request, report_id):
    try:
        report = FinancialReport.objects.get(id=report_id)
        
        # 检查权限
        if report.user and report.user != request.user:
            return Response({'error': '只能授权自己的报表'}, status=status.HTTP_403_FORBIDDEN)
        if report.project and not report.project.members.filter(id=request.user.id).exists():
            return Response({'error': '只有项目成员可以授权项目报表'}, status=status.HTTP_403_FORBIDDEN)
        
        report.is_authorized = not report.is_authorized
        if report.is_authorized:
            from django.utils import timezone
            report.authorized_at = timezone.now()
        else:
            report.authorized_at = None
        report.save()
        
        return Response({
            'message': f"报表已{'授权公开' if report.is_authorized else '取消授权'}",
            'is_authorized': report.is_authorized
        })
    except FinancialReport.DoesNotExist:
        return Response({'error': '报表不存在'}, status=status.HTTP_404_NOT_FOUND)

class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(
            Q(from_user=user) | Q(to_user=user) | Q(to_project__members=user)
        ).distinct().order_by('-created_at')

class ShareholderEquityListView(generics.ListAPIView):
    serializer_class = ShareholderEquitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        voting_round_id = self.request.query_params.get('voting_round')
        
        queryset = ShareholderEquity.objects.filter(
            Q(user=user) | Q(target_user=user) | Q(target_project__members=user)
        ).distinct()
        
        if voting_round_id:
            queryset = queryset.filter(voting_round_id=voting_round_id)
            
        return queryset.order_by('-created_at')

@api_view(['GET'])
def get_real_equity_holdings(request):
    """获取基于真实投资数据的股权持有情况"""
    from apps.voting.models import SelfEvaluation
    
    user = request.user
    voting_round_id = request.query_params.get('voting_round')
    
    if not voting_round_id:
        return Response({'error': '必须指定投票轮次'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 获取用户的所有投资记录（作为投资人）
        investments_made = SelfEvaluation.objects.filter(
            investor=user,
            voting_round_id=voting_round_id,
            is_approved=True
        ).order_by('-created_at')
        
        equity_holdings = []
        for investment in investments_made:
            if investment.entity_type == 'user':
                from apps.users.models import User
                target_user = User.objects.get(id=investment.entity_id)
                target_name = target_user.username
                target_type = '个人'
            else:  # project
                from apps.projects.models import Project
                target_project = Project.objects.get(id=investment.entity_id)
                target_name = target_project.name
                target_type = '项目'
            
            equity_holdings.append({
                'id': investment.id,
                'target_name': target_name,
                'target_type': target_type,
                'entity_type': investment.entity_type,
                'entity_id': investment.entity_id,
                'investment_amount': float(investment.investment_amount),
                'equity_percentage': float(investment.new_equity_percentage),
                'previous_equity': float(investment.previous_equity_percentage),
                'dilution': float(investment.dilution_percentage),
                'valuation_before': float(investment.previous_valuation),
                'valuation_after': float(investment.new_valuation),
                'created_at': investment.created_at.isoformat()
            })
        
        # 计算总投资和总估值
        total_investment = sum(item['investment_amount'] for item in equity_holdings)
        
        return Response({
            'equity_holdings': equity_holdings,
            'total_investment': total_investment,
            'data_source': 'real_self_evaluations'
        })
        
    except Exception as e:
        return Response({'error': f'获取股权数据失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def my_portfolio(request):
    """获取用户的投资组合 - 基于真实投资数据"""
    from apps.voting.models import SelfEvaluation
    
    user = request.user
    voting_round_id = request.query_params.get('voting_round')
    
    try:
        # 获取用户持有的股权（基于真实投资记录）
        investments_query = SelfEvaluation.objects.filter(
            investor=user,
            is_approved=True
        )
        
        if voting_round_id:
            investments_query = investments_query.filter(voting_round_id=voting_round_id)
        
        equity_data = []
        total_investment = 0
        
        for investment in investments_query:
            if investment.entity_type == 'user':
                from apps.users.models import User
                target_user = User.objects.get(id=investment.entity_id)
                target_name = target_user.username
            else:  # project
                from apps.projects.models import Project
                target_project = Project.objects.get(id=investment.entity_id)
                target_name = target_project.name
            
            equity_item = {
                'id': investment.id,
                'target_name': target_name,
                'target_type': investment.get_entity_type_display(),
                'investment_amount': float(investment.investment_amount),
                'equity_percentage': float(investment.new_equity_percentage),
                'current_valuation': float(investment.new_valuation),
                'voting_round': investment.voting_round.name,
                'created_at': investment.created_at.isoformat()
            }
            equity_data.append(equity_item)
            total_investment += float(investment.investment_amount)
        
        # 获取用户余额
        user_balance = getattr(user, 'balance', 0.0)
        user_total_received = getattr(user, 'total_received', 0.0)
        
        return Response({
            'total_investment': total_investment,
            'equity_holdings': equity_data,
            'user_balance': user_balance,
            'total_received': user_total_received,
            'data_source': 'real_investment_records'
        })
        
    except Exception as e:
        return Response({'error': f'获取投资组合失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_wechat_payment(request):
    """创建微信支付订单"""
    amount = request.data.get('amount')
    vote_id = request.data.get('vote_id')
    
    if not amount or not vote_id:
        return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 这里应该集成微信支付API
    # 为了演示，我们直接返回一个模拟的支付信息
    import uuid
    transaction_id = str(uuid.uuid4())
    
    return Response({
        'transaction_id': transaction_id,
        'amount': amount,
        'payment_url': f'https://pay.weixin.qq.com/mock/{transaction_id}',
        'qr_code': f'weixin://pay/{transaction_id}'
    })