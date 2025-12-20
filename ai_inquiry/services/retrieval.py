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

    使用模糊匹配（icontains），不需要问题完全一致。
    
    匹配策略：
    1. 提取问题中的关键词（去除停用词）
    2. 检查 question_pattern/title/content 中是否包含这些关键词
    
    例如：用户问"我口腔溃疡了"
    - 提取关键词："口腔溃疡"
    - 匹配到 question_pattern 为 "口腔溃疡,口疮,嘴巴溃疡" 的条目
    - 匹配到 title 中包含 "口腔溃疡" 的条目
    - 匹配到 content 中包含 "口腔溃疡" 的条目
    """
    qs = DentalKnowledgeArticle.objects.filter(is_active=True)
    
    # 提取问题中的关键词（去除常见停用词）
    stop_words = {
        '我', '了', '的', '是', '在', '有', '和', '就', '不', '人', '都', '一', '一个', 
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', 
        '自己', '这', '吗', '呢', '啊', '呀', '吧', '么', '什么', '怎么', '如何', '为什么', 
        '怎么办', '能', '可以', '应该', '需要', '想', '要', '请', '帮', '给'
    }
    
    # 简单分词：按空格、标点符号分割
    import re
    # 保留中文字符、数字、字母，去除标点
    words = re.findall(r'[\u4e00-\u9fa5]+|\d+|[a-zA-Z]+', question)
    
    # 提取关键词：去除停用词，保留长度>=2的词
    keywords = [word for word in words if word and word not in stop_words and len(word) >= 2]
    
    # 如果没有提取到关键词，使用原问题
    if not keywords:
        keywords = [question]
    
    # 构建查询：检查 question_pattern/title/content 中是否包含任意关键词
    query = Q()
    for keyword in keywords:
        query |= (
            Q(question_pattern__icontains=keyword)  # question_pattern 中包含关键词
            | Q(title__icontains=keyword)  # title 中包含关键词
            | Q(content__icontains=keyword)  # content 中包含关键词
        )
    
    # 同时保留原问题的完整匹配（以防关键词提取不准确）
    query |= (
        Q(question_pattern__icontains=question)
        | Q(title__icontains=question)
        | Q(content__icontains=question)
    )
    
    qs = qs.filter(query).distinct()
    
    return list(qs[:limit])


def retrieve_doctors_by_intent(
    intent: Dict[str, Any], 
    question: str = "",
    knowledge_list: List[DentalKnowledgeArticle] = None,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    根据结构化意图、用户问题和知识库内容智能推荐医生。

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
    
    推荐策略：
    1. 优先根据意图中的科室和病种匹配
    2. 如果匹配结果少，根据问题关键词和知识库标签扩展匹配
    3. 排序：在线医生 > 评分 > 评价数
    """
    dept_name = (intent.get("recommended_department") or "") if isinstance(intent, dict) else ""
    disease_category = (intent.get("disease_category") or "") if isinstance(intent, dict) else ""
    
    if knowledge_list is None:
        knowledge_list = []

    doctors = Doctor.objects.select_related("hospital").all()

    # 构建查询条件
    query = Q()
    
    # 1. 优先匹配：根据意图中的科室和病种
    if dept_name:
        query |= (
            Q(specialty__icontains=dept_name)
            | Q(introduction__icontains=dept_name)
            | Q(experience__icontains=dept_name)
        )
    
    if disease_category and disease_category != "未知":
        query |= (
            Q(specialty__icontains=disease_category)
            | Q(introduction__icontains=disease_category)
            | Q(experience__icontains=disease_category)
        )
    
    # 2. 扩展匹配：根据知识库标签匹配
    # 从知识库中提取标签关键词
    if knowledge_list:
        for knowledge in knowledge_list:
            if knowledge.tags:
                # tags 格式：逗号分隔，如 "龋齿,蛀牙,补牙,口腔内科"
                tags = [tag.strip() for tag in knowledge.tags.split(',') if tag.strip()]
                for tag in tags:
                    # 跳过太通用的标签（如"口腔内科"已经在科室匹配中处理）
                    if tag not in ['口腔内科', '口腔外科', '正畸科', '儿童口腔科']:
                        query |= (
                            Q(specialty__icontains=tag)
                            | Q(introduction__icontains=tag)
                            | Q(experience__icontains=tag)
                        )
    
    # 3. 如果还没有匹配条件，根据问题关键词匹配
    if not query and question:
        # 提取问题中的关键词（去除停用词）
        import re
        stop_words = {
            '我', '了', '的', '是', '在', '有', '和', '就', '不', '人', '都', '一', '一个', 
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', 
            '自己', '这', '吗', '呢', '啊', '呀', '吧', '么', '什么', '怎么', '如何', '为什么', 
            '怎么办', '能', '可以', '应该', '需要', '想', '要', '请', '帮', '给', '医生', '擅长'
        }
        words = re.findall(r'[\u4e00-\u9fa5]+|\d+|[a-zA-Z]+', question)
        keywords = [word for word in words if word and word not in stop_words and len(word) >= 2]
        
        # 专业相关关键词映射（将用户常用词映射到专业术语）
        specialty_mapping = {
            '正畸': '正畸',
            '矫正': '正畸',
            '牙齿矫正': '正畸',
            '牙矫正': '正畸',
            '种植': '种植',
            '种植牙': '种植',
            '补牙': '补牙',
            '根管': '根管',
            '根管治疗': '根管',
            '牙周': '牙周',
            '牙周病': '牙周',
            '口腔内科': '口腔内科',
            '口腔外科': '口腔外科',
            '儿童口腔': '儿童口腔',
            '口腔黏膜': '口腔黏膜',
            '龋齿': '龋齿',
            '蛀牙': '龋齿',
            '牙髓': '牙髓',
            '拔牙': '拔牙',
            '洗牙': '洗牙',
            '美白': '美白',
        }
        
        # 专业相关关键词列表（用于快速判断）
        specialty_keywords = list(specialty_mapping.keys())
        
        # 检查问题中是否包含专业相关关键词
        question_lower = question.lower()
        matched_specialty = None
        
        # 优先检查完整短语（如"牙齿矫正"）
        for user_term, db_term in specialty_mapping.items():
            if user_term in question:
                matched_specialty = db_term
                # 只匹配specialty字段，确保专业对口
                query |= Q(specialty__icontains=db_term)
                break
        
        # 如果没有匹配到完整短语，检查单个关键词
        if not matched_specialty:
            for keyword in keywords[:5]:
                # 如果是专业相关关键词，只匹配specialty字段
                if keyword in specialty_mapping:
                    matched_specialty = specialty_mapping[keyword]
                    query |= Q(specialty__icontains=matched_specialty)
                elif keyword in specialty_keywords or any(sk in keyword for sk in specialty_keywords):
                    # 如果关键词包含专业相关词，尝试匹配
                    for user_term, db_term in specialty_mapping.items():
                        if user_term in keyword or keyword in user_term:
                            query |= Q(specialty__icontains=db_term)
                            matched_specialty = db_term
                            break
        
        # 匹配医生姓名（如果关键词可能是姓名）
        for keyword in keywords[:5]:
            if len(keyword) >= 2 and len(keyword) <= 4:  # 姓名通常是2-4个字
                query |= Q(name__icontains=keyword)  # 匹配医生姓名
        
        # 如果已经匹配到专业，就不再匹配introduction/experience（确保专业对口）
        # 如果没有匹配到专业，才进行宽泛匹配
        if not matched_specialty:
            for keyword in keywords[:5]:
                query |= (
                    Q(specialty__icontains=keyword)
                    | Q(introduction__icontains=keyword)
                    | Q(experience__icontains=keyword)
                )
    
    # 应用查询条件
    has_exact_match = False
    if query:
        matched_doctors = doctors.filter(query).distinct()
        if matched_doctors.exists():
            doctors = matched_doctors
            has_exact_match = True
            # 对精确匹配的医生进行优先级排序
            from django.db.models import Case, When, IntegerField
            
            # 构建匹配优先级（专业匹配优先于其他匹配）
            priority_conditions = []
            
            # 1. specialty完全匹配（最高优先级）
            if dept_name:
                priority_conditions.append(
                    When(specialty__iexact=dept_name, then=1)
                )
            if disease_category and disease_category != "未知":
                priority_conditions.append(
                    When(specialty__iexact=disease_category, then=1)
                )
            
            # 2. specialty包含匹配（专业匹配优先级高）
            if dept_name:
                priority_conditions.append(
                    When(specialty__icontains=dept_name, then=2)
                )
            if disease_category and disease_category != "未知":
                priority_conditions.append(
                    When(specialty__icontains=disease_category, then=2)
                )
            
            # 3. 医生姓名匹配（如果用户提到具体医生姓名）
            # 从问题中提取可能的医生姓名
            import re
            words = re.findall(r'[\u4e00-\u9fa5]+', question)
            for word in words:
                if 2 <= len(word) <= 4:  # 姓名通常是2-4个字
                    priority_conditions.append(
                        When(name__icontains=word, then=2)  # 姓名匹配优先级也较高
                    )
            
            # 4. introduction/experience匹配（较低优先级）
            if dept_name:
                priority_conditions.append(
                    When(introduction__icontains=dept_name, then=3)
                )
                priority_conditions.append(
                    When(experience__icontains=dept_name, then=3)
                )
            
            if priority_conditions:
                doctors = doctors.annotate(
                    match_priority=Case(
                        *priority_conditions,
                        default=4,
                        output_field=IntegerField()
                    )
                ).order_by("match_priority", "-is_online", "-score", "-reviews")
            else:
                # 如果没有优先级条件，按在线状态、评分、评价数排序
                doctors = doctors.order_by("-is_online", "-score", "-reviews")
        else:
            # 如果没有精确匹配，尝试根据问题关键词进行专业匹配排序
            # 优先匹配专业相关的医生，而不是只看评分
            from django.db.models import Case, When, IntegerField
            priority_conditions = []
            
            # 提取专业相关关键词（使用映射）
            import re
            specialty_mapping = {
                '正畸': '正畸', '矫正': '正畸', '牙齿矫正': '正畸', '牙矫正': '正畸',
                '种植': '种植', '种植牙': '种植',
                '补牙': '补牙', '根管': '根管', '根管治疗': '根管',
                '牙周': '牙周', '牙周病': '牙周',
                '口腔内科': '口腔内科', '口腔外科': '口腔外科',
                '儿童口腔': '儿童口腔', '口腔黏膜': '口腔黏膜',
                '龋齿': '龋齿', '蛀牙': '龋齿', '牙髓': '牙髓',
                '拔牙': '拔牙', '洗牙': '洗牙', '美白': '美白',
            }
            words = re.findall(r'[\u4e00-\u9fa5]+', question)
            
            # 优先检查完整短语
            matched_specialty = None
            for user_term, db_term in specialty_mapping.items():
                if user_term in question:
                    matched_specialty = db_term
                    priority_conditions.append(
                        When(specialty__icontains=db_term, then=1)  # 专业匹配优先级最高
                    )
                    break
            
            # 如果没有匹配到完整短语，检查单个词
            if not matched_specialty:
                for word in words:
                    if word in specialty_mapping:
                        matched_specialty = specialty_mapping[word]
                        priority_conditions.append(
                            When(specialty__icontains=matched_specialty, then=1)
                        )
                    # 如果可能是医生姓名
                    if 2 <= len(word) <= 4:
                        priority_conditions.append(
                            When(name__icontains=word, then=1)  # 姓名匹配优先级也高
                        )
            
            if priority_conditions:
                doctors = doctors.annotate(
                    match_priority=Case(
                        *priority_conditions,
                        default=2,  # 没有专业匹配的医生优先级较低
                        output_field=IntegerField()
                    )
                ).order_by("match_priority", "-is_online", "-score", "-reviews")
            else:
                # 如果没有专业关键词，按在线状态、评分、评价数排序
                doctors = doctors.order_by("-is_online", "-score", "-reviews")
    else:
        # 如果没有匹配条件，尝试根据问题关键词进行专业匹配排序
        from django.db.models import Case, When, IntegerField
        priority_conditions = []
        
        # 提取专业相关关键词（使用映射）
        import re
        specialty_mapping = {
            '正畸': '正畸', '矫正': '正畸', '牙齿矫正': '正畸', '牙矫正': '正畸',
            '种植': '种植', '种植牙': '种植',
            '补牙': '补牙', '根管': '根管', '根管治疗': '根管',
            '牙周': '牙周', '牙周病': '牙周',
            '口腔内科': '口腔内科', '口腔外科': '口腔外科',
            '儿童口腔': '儿童口腔', '口腔黏膜': '口腔黏膜',
            '龋齿': '龋齿', '蛀牙': '龋齿', '牙髓': '牙髓',
            '拔牙': '拔牙', '洗牙': '洗牙', '美白': '美白',
        }
        words = re.findall(r'[\u4e00-\u9fa5]+', question)
        
        # 优先检查完整短语
        matched_specialty = None
        for user_term, db_term in specialty_mapping.items():
            if user_term in question:
                matched_specialty = db_term
                priority_conditions.append(
                    When(specialty__icontains=db_term, then=1)  # 专业匹配优先级最高
                )
                break
        
        # 如果没有匹配到完整短语，检查单个词
        if not matched_specialty:
            for word in words:
                if word in specialty_mapping:
                    matched_specialty = specialty_mapping[word]
                    priority_conditions.append(
                        When(specialty__icontains=matched_specialty, then=1)
                    )
                # 如果可能是医生姓名
                if 2 <= len(word) <= 4:
                    priority_conditions.append(
                        When(name__icontains=word, then=1)  # 姓名匹配优先级也高
                    )
        
        if priority_conditions:
            doctors = doctors.annotate(
                match_priority=Case(
                    *priority_conditions,
                    default=2,  # 没有专业匹配的医生优先级较低
                    output_field=IntegerField()
                )
            ).order_by("match_priority", "-is_online", "-score", "-reviews")
        else:
            # 如果没有专业关键词，按在线状态、评分、评价数排序
            doctors = doctors.order_by("-is_online", "-score", "-reviews")
    
    result: List[Dict[str, Any]] = []
    for d in doctors:
        hospital_name = d.hospital.name if getattr(d, "hospital", None) else ""

        # 组合医生的专长信息，包含specialty、introduction、experience
        # 这样AI可以根据这些信息判断是否适合用户描述的症状
        good_at_parts = []
        if d.specialty:
            good_at_parts.append(f"专科：{d.specialty}")
        if d.introduction:
            good_at_parts.append(f"简介：{d.introduction}")
        if d.experience:
            good_at_parts.append(f"经验：{d.experience}")
        
        good_at = "；".join(good_at_parts) if good_at_parts else "暂无详细信息"

        result.append(
            {
                "id": d.id,
                "name": d.name,
                "department_name": hospital_name,
                "title": d.title,
                "specialty": d.specialty or "",  # 专科
                "introduction": d.introduction or "",  # 简介
                "experience": d.experience or "",  # 经验
                "good_at": good_at,  # 综合专长描述
                "is_online": d.is_online,  # 是否在线，用于紧急时间推荐
                "score": d.score,  # 评分
                "reviews": d.reviews,  # 评价数
                "next_available_time": "暂无排班信息",  # 当前系统无排班表，返回提示文案
                "is_exact_match": has_exact_match,  # 是否为精确匹配
            }
        )

    return result


