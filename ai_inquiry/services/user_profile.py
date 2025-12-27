"""
用户画像服务（方案三：个性化用户画像）
分析用户历史行为，计算用户偏好
"""
from typing import Dict, Any, Optional
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from ai_inquiry.models import UserProfile, UserBehavior
from doctors.models import Doctor
from appointments.models import Appointment


def calculate_specialty_preference(user) -> Dict[str, float]:
    """
    计算用户的专科偏好
    
    Args:
        user: 用户对象
        
    Returns:
        专科偏好字典，如 {"正畸": 0.8, "种植": 0.2}
    """
    # 获取用户的所有预约记录
    appointments = Appointment.objects.filter(user=user, status__in=['completed', 'upcoming'])
    
    if not appointments.exists():
        return {}
    
    # 统计各专科的预约次数
    specialty_counts = {}
    for apt in appointments:
        specialty = apt.doctor.specialty
        if specialty:
            specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1
    
    # 归一化（转换为0-1之间的概率）
    total = sum(specialty_counts.values())
    if total == 0:
        return {}
    
    specialty_preference = {
        k: v / total for k, v in specialty_counts.items()
    }
    
    return specialty_preference


def calculate_hospital_preference(user) -> Dict[str, float]:
    """
    计算用户的医院偏好
    
    Args:
        user: 用户对象
        
    Returns:
        医院偏好字典
    """
    appointments = Appointment.objects.filter(user=user, status__in=['completed', 'upcoming'])
    
    if not appointments.exists():
        return {}
    
    hospital_counts = {}
    for apt in appointments:
        hospital_name = apt.hospital.name if apt.hospital else None
        if hospital_name:
            hospital_counts[hospital_name] = hospital_counts.get(hospital_name, 0) + 1
    
    total = sum(hospital_counts.values())
    if total == 0:
        return {}
    
    hospital_preference = {
        k: v / total for k, v in hospital_counts.items()
    }
    
    return hospital_preference


def calculate_time_preference(user) -> Optional[str]:
    """
    计算用户的时间偏好
    
    Args:
        user: 用户对象
        
    Returns:
        时间偏好：'morning', 'afternoon', 'evening' 或 None
    """
    appointments = Appointment.objects.filter(
        user=user,
        status__in=['completed', 'upcoming']
    )
    
    if not appointments.exists():
        return None
    
    time_counts = {'morning': 0, 'afternoon': 0, 'evening': 0}
    
    for apt in appointments:
        if apt.appointment_time:
            try:
                hour = int(apt.appointment_time.split(':')[0])
                if 6 <= hour < 12:
                    time_counts['morning'] += 1
                elif 12 <= hour < 18:
                    time_counts['afternoon'] += 1
                elif 18 <= hour < 24:
                    time_counts['evening'] += 1
            except (ValueError, IndexError):
                continue
    
    # 返回最多的时段
    if sum(time_counts.values()) == 0:
        return None
    
    return max(time_counts.items(), key=lambda x: x[1])[0]


def calculate_doctor_feature_preference(user) -> Dict[str, float]:
    """
    计算用户对医生特征的偏好（评分权重 vs 评价数权重）
    
    Args:
        user: 用户对象
        
    Returns:
        特征偏好字典，如 {"score_weight": 0.6, "reviews_weight": 0.4}
    """
    # 获取用户预约过的医生
    appointments = Appointment.objects.filter(user=user, status__in=['completed', 'upcoming'])
    doctor_ids = appointments.values_list('doctor_id', flat=True).distinct()
    
    if not doctor_ids:
        # 默认偏好
        return {"score_weight": 0.5, "reviews_weight": 0.5}
    
    doctors = Doctor.objects.filter(id__in=doctor_ids)
    
    # 计算平均评分和平均评价数
    avg_score = doctors.aggregate(avg=Avg('score'))['avg'] or 0
    avg_reviews = doctors.aggregate(avg=Avg('reviews'))['avg'] or 0
    
    # 如果用户选择的医生评分普遍较高，说明偏好高评分
    # 如果用户选择的医生评价数普遍较多，说明偏好高评价数
    # 这里简化处理：根据平均值判断
    total_weight = 1.0
    
    # 归一化评分和评价数（假设评分范围0-5，评价数范围0-1000）
    normalized_score = avg_score / 5.0
    normalized_reviews = min(avg_reviews / 1000.0, 1.0)
    
    if normalized_score + normalized_reviews == 0:
        return {"score_weight": 0.5, "reviews_weight": 0.5}
    
    # 根据归一化值计算权重
    score_weight = normalized_score / (normalized_score + normalized_reviews)
    reviews_weight = 1.0 - score_weight
    
    return {
        "score_weight": float(score_weight),
        "reviews_weight": float(reviews_weight)
    }


def calculate_price_sensitivity(user) -> float:
    """
    计算用户的价格敏感度（简化版本）
    
    注意：当前系统没有价格字段，这里使用简化逻辑
    如果未来有价格数据，可以根据用户选择的医生价格区间计算
    
    Args:
        user: 用户对象
        
    Returns:
        价格敏感度（0-1之间）
    """
    # 简化处理：根据用户行为判断
    # 如果用户经常选择高评分医生（可能价格较高），敏感度较低
    # 如果用户经常选择评价数多的医生（可能价格适中），敏感度中等
    
    appointments = Appointment.objects.filter(user=user, status__in=['completed', 'upcoming'])
    
    if not appointments.exists():
        return 0.5  # 默认中等敏感度
    
    doctor_ids = appointments.values_list('doctor_id', flat=True).distinct()
    doctors = Doctor.objects.filter(id__in=doctor_ids)
    
    avg_score = doctors.aggregate(avg=Avg('score'))['avg'] or 0
    
    # 如果平均评分较高，说明用户不太在意价格（敏感度低）
    # 如果平均评分较低，说明用户可能更在意价格（敏感度高）
    # 这里简化处理：评分越高，敏感度越低
    sensitivity = 1.0 - (avg_score / 5.0)
    
    return max(0.0, min(1.0, sensitivity))


def update_user_profile(user, force_update: bool = False):
    """
    更新用户画像
    
    Args:
        user: 用户对象
        force_update: 是否强制更新（即使最近已更新过）
    """
    # 检查是否需要更新（如果最近1小时内更新过，且不是强制更新，则跳过）
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if not force_update and not created:
        time_since_update = timezone.now() - profile.updated_at
        if time_since_update < timedelta(hours=1):
            return  # 最近已更新，跳过
    
    # 计算各项偏好
    specialty_preference = calculate_specialty_preference(user)
    hospital_preference = calculate_hospital_preference(user)
    time_preference = calculate_time_preference(user)
    doctor_feature_preference = calculate_doctor_feature_preference(user)
    price_sensitivity = calculate_price_sensitivity(user)
    
    # 更新画像
    profile.specialty_preference = specialty_preference
    profile.hospital_preference = hospital_preference
    profile.time_preference = time_preference
    profile.doctor_feature_preference = doctor_feature_preference
    profile.price_sensitivity = price_sensitivity
    profile.save()
    
    return profile


def get_user_profile(user) -> UserProfile:
    """
    获取用户画像（如果不存在则创建）
    
    Args:
        user: 用户对象
        
    Returns:
        用户画像对象
    """
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # 如果是新创建的，不立即计算（避免性能问题）
    # 等有足够数据后再计算
    # if created:
    #     update_user_profile(user, force_update=True)
    
    return profile

