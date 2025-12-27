"""
智能推荐服务（方案二：协同过滤 + 内容推荐）
根据用户历史行为智能推荐医生
"""
import math
from typing import List, Dict, Any, Set, Optional
from collections import defaultdict
from django.db.models import Q, Count, Avg

from doctors.models import Doctor
from ai_inquiry.models import UserBehavior, UserProfile
from ai_inquiry.services.user_profile import get_user_profile


def calculate_user_similarity(user1_id: int, user2_id: int) -> float:
    """
    计算两个用户的相似度（基于协同过滤）
    
    使用余弦相似度计算：找到两个用户都交互过的医生，计算相似度
    
    Args:
        user1_id: 用户1的ID
        user2_id: 用户2的ID
        
    Returns:
        相似度分数（0-1之间）
    """
    # 获取两个用户的行为记录
    user1_behaviors = UserBehavior.objects.filter(user_id=user1_id, doctor__isnull=False)
    user2_behaviors = UserBehavior.objects.filter(user_id=user2_id, doctor__isnull=False)
    
    # 构建用户-医生评分矩阵
    user1_doctors = {}
    user2_doctors = {}
    
    # 用户1的医生评分（根据行为类型和评分计算）
    for behavior in user1_behaviors:
        doctor_id = behavior.doctor_id
        # 不同行为的权重不同
        weight = {
            'make_appointment': 3.0,
            'rate_doctor': 2.0,
            'click_doctor': 1.0,
            'view_doctor_detail': 1.5,
        }.get(behavior.action, 1.0)
        
        score = behavior.score * weight
        user1_doctors[doctor_id] = user1_doctors.get(doctor_id, 0) + score
    
    # 用户2的医生评分
    for behavior in user2_behaviors:
        doctor_id = behavior.doctor_id
        weight = {
            'make_appointment': 3.0,
            'rate_doctor': 2.0,
            'click_doctor': 1.0,
            'view_doctor_detail': 1.5,
        }.get(behavior.action, 1.0)
        
        score = behavior.score * weight
        user2_doctors[doctor_id] = user2_doctors.get(doctor_id, 0) + score
    
    # 找到共同交互的医生
    common_doctors = set(user1_doctors.keys()) & set(user2_doctors.keys())
    
    if not common_doctors:
        return 0.0
    
    # 计算余弦相似度
    dot_product = sum(user1_doctors[d] * user2_doctors[d] for d in common_doctors)
    
    norm1 = math.sqrt(sum(v ** 2 for v in user1_doctors.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in user2_doctors.values()))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def find_similar_users(user_id: int, limit: int = 10, min_similarity: float = 0.1) -> List[Dict[str, Any]]:
    """
    找到与当前用户相似的其他用户
    
    Args:
        user_id: 当前用户ID
        limit: 返回的相似用户数量
        min_similarity: 最小相似度阈值
        
    Returns:
        相似用户列表，包含用户ID和相似度
    """
    # 获取所有有行为的其他用户
    other_user_ids = UserBehavior.objects.exclude(
        user_id=user_id
    ).values_list('user_id', flat=True).distinct()
    
    similar_users = []
    for other_user_id in other_user_ids:
        similarity = calculate_user_similarity(user_id, other_user_id)
        if similarity >= min_similarity:
            similar_users.append({
                'user_id': other_user_id,
                'similarity': similarity
            })
    
    # 按相似度降序排序
    similar_users.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similar_users[:limit]


def collaborative_filtering_recommend(
    user_id: int,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    基于协同过滤的推荐
    
    找到相似用户喜欢的医生，推荐给当前用户
    
    Args:
        user_id: 用户ID
        limit: 返回的医生数量
        
    Returns:
        推荐医生列表，包含医生信息和推荐分数
    """
    # 找到相似用户
    similar_users = find_similar_users(user_id, limit=20)
    
    if not similar_users:
        return []
    
    # 统计相似用户喜欢的医生（加权）
    doctor_scores = defaultdict(float)
    
    for similar_user in similar_users:
        similarity = similar_user['similarity']
        other_user_id = similar_user['user_id']
        
        # 获取该用户的行为
        behaviors = UserBehavior.objects.filter(
            user_id=other_user_id,
            doctor__isnull=False,
            action__in=['make_appointment', 'rate_doctor', 'click_doctor']
        )
        
        for behavior in behaviors:
            doctor_id = behavior.doctor_id
            # 根据行为类型和相似度计算分数
            weight = {
                'make_appointment': 3.0,
                'rate_doctor': 2.0,
                'click_doctor': 1.0,
            }.get(behavior.action, 1.0)
            
            score = behavior.score * weight * similarity
            doctor_scores[doctor_id] += score
    
    # 获取医生信息
    doctor_ids = list(doctor_scores.keys())
    if not doctor_ids:
        return []
    
    doctors = Doctor.objects.filter(id__in=doctor_ids).select_related('hospital')
    
    # 构建推荐结果
    recommendations = []
    for doctor in doctors:
        recommendations.append({
            'doctor': doctor,
            'cf_score': doctor_scores[doctor.id],  # 协同过滤分数
        })
    
    # 按协同过滤分数降序排序
    recommendations.sort(key=lambda x: x['cf_score'], reverse=True)
    
    return recommendations[:limit]


def content_based_recommend(
    user_id: int,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    基于内容的推荐
    
    根据用户历史偏好，推荐具有相似特征的医生
    
    Args:
        user_id: 用户ID
        limit: 返回的医生数量
        
    Returns:
        推荐医生列表，包含医生信息和推荐分数
    """
    # 获取用户画像
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return []
        
        try:
            profile = get_user_profile(user)
        except UserProfile.DoesNotExist:
            # 如果用户画像不存在，返回空列表（使用基础推荐）
            return []
    except Exception as e:
        # 如果获取用户画像失败，返回空列表
        print(f"获取用户画像失败: {e}")
        return []
    
    # 获取用户历史交互的医生
    user_behaviors = UserBehavior.objects.filter(
        user_id=user_id,
        doctor__isnull=False
    )
    
    user_doctor_ids = set(user_behaviors.values_list('doctor_id', flat=True))
    
    # 分析用户偏好的医生特征
    if user_doctor_ids:
        user_doctors = Doctor.objects.filter(id__in=user_doctor_ids)
        
        # 计算用户偏好的专科
        specialty_counts = defaultdict(int)
        for doctor in user_doctors:
            if doctor.specialty:
                specialty_counts[doctor.specialty] += 1
        
        # 计算用户偏好的平均评分和评价数
        avg_score = user_doctors.aggregate(avg=Avg('score'))['avg'] or 0
        avg_reviews = user_doctors.aggregate(avg=Avg('reviews'))['avg'] or 0
    else:
        # 如果没有历史行为，使用画像中的偏好
        specialty_counts = profile.specialty_preference or {}
        avg_score = 4.0  # 默认值
        avg_reviews = 100  # 默认值
    
    # 找到具有相似特征的医生（排除用户已交互过的）
    all_doctors = Doctor.objects.exclude(id__in=user_doctor_ids).select_related('hospital')
    
    recommendations = []
    for doctor in all_doctors:
        cb_score = 0.0
        
        # 1. 专科匹配（权重最高）
        if doctor.specialty and specialty_counts:
            specialty_match = specialty_counts.get(doctor.specialty, 0)
            if specialty_match > 0:
                # 归一化
                max_count = max(specialty_counts.values()) if specialty_counts else 1
                cb_score += (specialty_match / max_count) * 0.5
        
        # 2. 评分相似度（用户偏好高评分，推荐高评分医生）
        score_diff = abs(doctor.score - avg_score)
        score_similarity = 1.0 - (score_diff / 5.0)  # 归一化
        cb_score += score_similarity * 0.3
        
        # 3. 评价数相似度
        reviews_diff = abs(doctor.reviews - avg_reviews)
        reviews_similarity = 1.0 - min(reviews_diff / 1000.0, 1.0)
        cb_score += reviews_similarity * 0.2
        
        if cb_score > 0:
            recommendations.append({
                'doctor': doctor,
                'cb_score': cb_score,  # 内容推荐分数
            })
    
    # 按内容推荐分数降序排序
    recommendations.sort(key=lambda x: x['cb_score'], reverse=True)
    
    return recommendations[:limit]


def hybrid_recommend(
    user_id: int,
    intent: Optional[Dict[str, Any]] = None,
    question: str = "",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    混合推荐：结合协同过滤、内容推荐和基础规则
    
    Args:
        user_id: 用户ID
        intent: 用户意图（可选）
        question: 用户问题（可选）
        limit: 返回的医生数量
        
    Returns:
        推荐医生列表
    """
    # 1. 协同过滤推荐
    cf_recommendations = collaborative_filtering_recommend(user_id, limit=limit * 2)
    
    # 2. 内容推荐
    cb_recommendations = content_based_recommend(user_id, limit=limit * 2)
    
    # 3. 基础规则推荐（基于意图和问题，使用原有逻辑）
    from ai_inquiry.services.retrieval import retrieve_doctors_by_intent
    base_recommendations = retrieve_doctors_by_intent(
        intent=intent or {},
        question=question,
        limit=limit * 2
    )
    
    # 4. 合并推荐结果
    doctor_scores = defaultdict(lambda: {
        'doctor': None,
        'cf_score': 0.0,
        'cb_score': 0.0,
        'base_score': 0.0,
        'final_score': 0.0
    })
    
    # 协同过滤分数（权重0.4）
    for rec in cf_recommendations:
        doctor_id = rec['doctor'].id
        doctor_scores[doctor_id]['doctor'] = rec['doctor']
        doctor_scores[doctor_id]['cf_score'] = rec['cf_score']
    
    # 内容推荐分数（权重0.4）
    for rec in cb_recommendations:
        doctor_id = rec['doctor'].id
        if doctor_scores[doctor_id]['doctor'] is None:
            doctor_scores[doctor_id]['doctor'] = rec['doctor']
        doctor_scores[doctor_id]['cb_score'] = rec['cb_score']
    
    # 基础规则分数（权重0.2）
    # 将基础推荐转换为分数（根据排序位置）
    for i, rec in enumerate(base_recommendations):
        doctor_id = rec.get('id')
        if doctor_id:
            if doctor_scores[doctor_id]['doctor'] is None:
                # 需要从数据库获取医生对象
                try:
                    doctor = Doctor.objects.get(id=doctor_id)
                    doctor_scores[doctor_id]['doctor'] = doctor
                except Doctor.DoesNotExist:
                    continue
            # 基础分数：位置越靠前，分数越高
            doctor_scores[doctor_id]['base_score'] = (len(base_recommendations) - i) / len(base_recommendations)
    
    # 5. 计算最终分数
    for doctor_id, scores in doctor_scores.items():
        if scores['doctor'] is None:
            continue
        
        # 归一化各分数到0-1范围
        # 协同过滤和内容推荐分数已经相对归一化，基础分数也已经归一化
        
        # 混合分数
        final_score = (
            scores['cf_score'] * 0.4 +
            scores['cb_score'] * 0.4 +
            scores['base_score'] * 0.2
        )
        
        scores['final_score'] = final_score
    
    # 6. 按最终分数排序
    final_recommendations = [
        {
            'doctor': scores['doctor'],
            'score': scores['final_score'],
            'cf_score': scores['cf_score'],
            'cb_score': scores['cb_score'],
            'base_score': scores['base_score'],
        }
        for scores in doctor_scores.values()
        if scores['doctor'] is not None
    ]
    
    final_recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    return final_recommendations[:limit]

