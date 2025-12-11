"""
医院序列化器
"""
from rest_framework import serializers
from .models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    """医院序列化器"""
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'phone', 'latitude', 'longitude',
            'image', 'rating', 'review_count', 'description', 'business_hours',
            'visit_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'visit_count', 'created_at', 'updated_at']

