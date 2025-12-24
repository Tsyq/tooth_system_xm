"""
医生评价序列化器
"""
from rest_framework import serializers
from records.models import Record


class DoctorReviewSerializer(serializers.ModelSerializer):
    """医生评价序列化器（从病历中提取）- 仅返回评价相关必要信息"""
    diagnosis = serializers.CharField(read_only=True, help_text='用户病症/诊断')
    
    class Meta:
        model = Record
        fields = ['rating', 'comment', 'diagnosis', 'created_at']
        read_only_fields = fields
