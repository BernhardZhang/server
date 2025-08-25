from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'student_id', 'balance', 'total_invested', 'total_received')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'student_id')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('学生信息', {'fields': ('student_id', 'phone', 'avatar')}),
        ('财务信息', {'fields': ('balance', 'total_invested', 'total_received')}),
    )