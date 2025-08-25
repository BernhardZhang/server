from rest_framework import serializers
from .models import AnalysisReport, DataMetric

class AnalysisReportSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)

    class Meta:
        model = AnalysisReport
        fields = ('id', 'title', 'report_type', 'creator', 'creator_name', 'data', 'summary', 'created_at', 'updated_at')

class AnalysisReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisReport
        fields = ('title', 'report_type', 'data', 'summary')

class DataMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataMetric
        fields = ('id', 'name', 'description', 'metric_type', 'value', 'timestamp')