from django.contrib import admin
from .models import Consultation, Message


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'doctor', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__name', 'doctor__name']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'consultation', 'sender', 'text', 'time']
    list_filter = ['sender', 'time']
    search_fields = ['text']

