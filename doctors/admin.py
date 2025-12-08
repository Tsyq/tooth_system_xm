from django.contrib import admin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'title', 'specialty', 'hospital', 'score', 'is_online', 'created_at']
    list_filter = ['specialty', 'is_online', 'is_admin', 'created_at']
    search_fields = ['name', 'title', 'specialty']

