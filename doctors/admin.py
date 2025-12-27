from django.contrib import admin
from .models import Doctor, Schedule


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'title', 'specialty', 'hospital', 'score', 'is_online', 'created_at']
    list_filter = ['specialty', 'is_online', 'is_admin', 'created_at']
    search_fields = ['name', 'title', 'specialty']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """排班管理"""
    list_display = ['id', 'doctor', 'hospital', 'date', 'status', 'created_at']
    list_filter = ['status', 'hospital', 'date']
    search_fields = ['doctor__name', 'hospital__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'

