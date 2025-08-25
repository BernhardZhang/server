from django.contrib import admin
from .models import PointsRecord, PointsTransaction, PointsReward, PointsRedemption

@admin.register(PointsRecord)
class PointsRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_type', 'amount', 'description', 'created_at']
    list_filter = ['record_type', 'created_at']
    search_fields = ['user__username', 'description']

@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__username', 'to_user__username', 'transaction_id']

@admin.register(PointsReward)
class PointsRewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'points_required', 'reward_type', 'stock', 'is_active']
    list_filter = ['reward_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']

@admin.register(PointsRedemption)
class PointsRedemptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'points_spent', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'reward__name']