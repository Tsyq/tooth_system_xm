from django.contrib import admin
from .models import Hospital


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'address', 'phone', 'rating', 'appointment_count', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['name', 'address']

