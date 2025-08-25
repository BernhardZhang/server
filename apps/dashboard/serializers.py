from rest_framework import serializers
from .models import DashboardWidget, UserPreference

class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = ('id', 'name', 'widget_type', 'config', 'position_x', 'position_y', 
                 'width', 'height', 'is_active', 'created_at', 'updated_at')

class DashboardWidgetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = ('name', 'widget_type', 'config', 'position_x', 'position_y', 'width', 'height')

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ('default_view', 'theme', 'language', 'notifications_enabled', 'auto_refresh_interval')