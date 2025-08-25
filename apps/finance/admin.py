from django.contrib import admin
from .models import FinancialReport, Transaction, ShareholderEquity

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('get_entity', 'report_type', 'voting_round', 'total_assets', 'equity', 'net_profit', 'is_authorized', 'created_at')
    list_filter = ('report_type', 'is_authorized', 'voting_round', 'created_at')
    search_fields = ('user__username', 'project__name')
    
    def get_entity(self, obj):
        return obj.user.username if obj.user else obj.project.name
    get_entity.short_description = '实体'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'get_target', 'amount', 'transaction_type', 'is_completed', 'created_at')
    list_filter = ('transaction_type', 'is_completed', 'created_at')
    search_fields = ('from_user__username', 'to_user__username', 'to_project__name', 'transaction_id')
    
    def get_target(self, obj):
        return obj.to_user.username if obj.to_user else obj.to_project.name
    get_target.short_description = '目标'

@admin.register(ShareholderEquity)
class ShareholderEquityAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_target', 'investment_amount', 'equity_percentage', 'voting_round', 'created_at')
    list_filter = ('voting_round', 'created_at')
    search_fields = ('user__username', 'target_user__username', 'target_project__name')
    
    def get_target(self, obj):
        return obj.target_user.username if obj.target_user else obj.target_project.name
    get_target.short_description = '投资目标'