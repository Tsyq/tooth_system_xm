from django.contrib import admin
from .models import Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'doctor', 'hospital', 'date', 'diagnosis', 'rated', 'rating', 'created_at']
    list_filter = ['date', 'rated', 'created_at']
    search_fields = ['diagnosis', 'content']

