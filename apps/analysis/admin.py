from django.contrib import admin
from .models import AnalysisReport, DataMetric

@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'creator', 'created_at']
    list_filter = ['report_type', 'created_at']
    search_fields = ['title', 'creator__username']

@admin.register(DataMetric)
class DataMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'metric_type', 'timestamp']
    list_filter = ['metric_type', 'timestamp']
    search_fields = ['name', 'description']