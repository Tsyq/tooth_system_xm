"""
知识检索与医生推荐逻辑。

说明：
- 完全基于当前项目已有模型，不额外引入 Department / Schedule 表；
- 医生推荐主要依赖 Doctor.specialty / introduction / score / reviews 等字段。
"""
from typing import Any, Dict, List

from django.db.models import Q

from ai_inquiry.models import DentalKnowledgeArticle
from doctors.models import Doctor


def retrieve_knowledge_snippets(question: str, limit: int = 3) -> List[DentalKnowledgeArticle]:
    """
    从牙科知识库中检索与问题相关的知识条目。

    简单实现：title / content / question_pattern 的 icontains 模糊匹配。
    后续如果需要，可以在这里替换为向量检索（RAG）方案。
    """
    qs = DentalKnowledgeArticle.objects.filter(is_active=True)
    qs = qs.filter(
        Q(title__icontains=question)
        | Q(content__icontains=question)
        | Q(question_pattern__icontains=question)
    )
    return list(qs[:limit])


def retrieve_doctors_by_intent(intent: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    根据结构化意图推荐医生。

    intent 示例:
    {
        "disease_category": "龋齿",
        "recommended_department": "口腔内科",
        "priority_level": "normal"
    }

    结合当前系统的 Doctor 模型字段：
    - specialty: 专科（可视作推荐科室/方向）
    - introduction / experience: 文本中也可能包含相关关键词
    - hospital: 用于展示医院名称
    """
    dept_name = (intent.get("recommended_department") or "") if isinstance(intent, dict) else ""
    disease_category = (intent.get("disease_category") or "") if isinstance(intent, dict) else ""

    doctors = Doctor.objects.select_related("hospital").all()

    # 按推荐科室 / 方向过滤（specialty / introduction / experience）
    if dept_name:
        doctors = doctors.filter(
            Q(specialty__icontains=dept_name)
            | Q(introduction__icontains=dept_name)
            | Q(experience__icontains=dept_name)
        )

    # 按疑似病种关键字进一步过滤
    if disease_category and disease_category != "未知":
        doctors = doctors.filter(
            Q(specialty__icontains=disease_category)
            | Q(introduction__icontains=disease_category)
            | Q(experience__icontains=disease_category)
        )

    # 排序逻辑：优先在线医生，其次评分、评价数
    doctors = doctors.order_by("-is_online", "-score", "-reviews")[:limit]

    result: List[Dict[str, Any]] = []
    for d in doctors:
        hospital_name = d.hospital.name if getattr(d, "hospital", None) else ""

        # 当前 Doctor 模型没有 good_at 字段，这里用 specialty+experience 组合一个简要说明
        good_at = d.specialty
        if d.experience:
            good_at = f"{d.specialty}；{d.experience}"

        result.append(
            {
                "id": d.id,
                "name": d.name,
                "department_name": hospital_name,
                "title": d.title,
                "good_at": good_at,
                "next_available_time": None,  # 当前系统无排班表，这里先返回 None
            }
        )

    return result


