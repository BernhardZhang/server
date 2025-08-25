from rest_framework import serializers
from .models import FinancialReport, Transaction, ShareholderEquity

class FinancialReportSerializer(serializers.ModelSerializer):
    entity_name = serializers.SerializerMethodField()
    entity_type = serializers.SerializerMethodField()

    class Meta:
        model = FinancialReport
        fields = ('id', 'user', 'project', 'entity_name', 'entity_type', 'report_type', 'data_source', 'voting_round', 
                 'total_assets', 'current_assets', 'fixed_assets', 'total_liabilities', 'equity',
                 'revenue', 'costs', 'gross_profit', 'operating_expenses', 'net_profit',
                 'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow', 'net_cash_flow',
                 'is_authorized', 'authorized_at', 'created_at')

    def get_entity_name(self, obj):
        return obj.user.username if obj.user else obj.project.name

    def get_entity_type(self, obj):
        return 'user' if obj.user else 'project'

class FinancialReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = ('user', 'project', 'report_type', 'voting_round', 
                 'total_assets', 'current_assets', 'fixed_assets', 'total_liabilities', 'equity',
                 'revenue', 'costs', 'operating_expenses',
                 'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow')

class TransactionSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.username', read_only=True)
    to_user_name = serializers.CharField(source='to_user.username', read_only=True)
    to_project_name = serializers.CharField(source='to_project.name', read_only=True)

    class Meta:
        model = Transaction
        fields = ('id', 'from_user', 'from_user_name', 'to_user', 'to_user_name', 'to_project', 'to_project_name',
                 'amount', 'transaction_type', 'description', 'transaction_id', 'is_completed', 'created_at')

class ShareholderEquitySerializer(serializers.ModelSerializer):
    shareholder_name = serializers.CharField(source='user.username', read_only=True)
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = ShareholderEquity
        fields = ('id', 'user', 'shareholder_name', 'target_user', 'target_project', 'target_name',
                 'investment_amount', 'equity_percentage', 'voting_round', 'created_at')

    def get_target_name(self, obj):
        return obj.target_user.username if obj.target_user else obj.target_project.name