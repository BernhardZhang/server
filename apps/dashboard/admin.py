from django.contrib import admin
from .models import DashboardWidget, UserPreference

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'user', 'is_active', 'created_at']
    list_filter = ['widget_type', 'is_active', 'created_at']
    search_fields = ['name', 'user__username']

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_view', 'theme', 'language', 'notifications_enabled']
    list_filter = ['theme', 'language', 'notifications_enabled']
    search_fields = ['user__username']