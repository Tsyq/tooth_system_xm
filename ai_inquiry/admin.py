from django.contrib import admin
from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'question', 'created_at']
    list_filter = ['created_at']
    search_fields = ['question', 'answer']

