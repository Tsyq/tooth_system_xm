"""
Prompt 模板与构造工具。

包含两类 Prompt：
- 意图抽取：将自然语言描述转换为结构化 JSON（病症类别、推荐方向、紧急程度）；
- 回答生成：结合对话历史、知识库结果和推荐医生，生成最终中文回答。
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ai_inquiry.models import DentalKnowledgeArticle


INTENT_EXTRACTION_SYSTEM_PROMPT = """你是一个牙科分诊助手。请根据用户描述，提取结构化的就诊意图信息。

**重要：你必须只输出一个有效的JSON对象，不要输出任何其他文字、解释、代码块标记或换行。**

输出格式示例：
{"disease_category": "龋齿", "recommended_department": "口腔内科", "priority_level": "normal"}

JSON 字段说明：
- "disease_category": 可能的病症类别（如：龋齿、牙髓炎、牙周炎、正畸需求 等，没有把握就填 "未知"）
- "recommended_department": 建议就诊的方向/专科名称（如：口腔内科、口腔外科、正畸科、儿童口腔科 等，如果没有明确方向可以填 null）
- "priority_level": 必须是以下三个值之一："info"（仅咨询）、"normal"（建议就诊）、"urgent"（建议尽快就医）

注意：如果提供了年龄、性别、过敏史等信息，请结合这些信息判断：
- 年龄：儿童（<12岁）建议儿童口腔科；青少年（12-18岁）常见正畸需求；老年人（>60岁）可能涉及修复、种植等
- 性别：某些疾病在不同性别中发病率不同
- 过敏史：如果有过敏史，在推荐治疗方案时需要考虑

**再次强调：只输出JSON对象，不要输出```json标记或其他任何文字。**"""


def build_intent_prompt(question: str, extra_info: Dict[str, Any]) -> str:
    """构造意图抽取 Prompt 文本。"""
    return (
        INTENT_EXTRACTION_SYSTEM_PROMPT
        + "\n用户描述如下：\n"
        + question
        + "\n用户额外信息："
        + json.dumps(extra_info, ensure_ascii=False)
    )


def build_answer_prompt(
    question: str,
    history: List[Dict[str, str]],
    knowledge_list: List[DentalKnowledgeArticle],
    recommended_doctors: List[Dict[str, Any]],
    current_datetime: datetime = None,
    extra_info: Dict[str, Any] = None,
) -> str:
    """
    生成最终回答的 Prompt。

    history: [{"role": "user"/"assistant", "content": "..."}]
    current_datetime: 当前日期时间，用于AI理解"今天"、"明天"等时间表达
    extra_info: 用户额外信息，包括年龄、性别、过敏史等
    """
    # 如果没有提供时间，使用当前时间
    if current_datetime is None:
        current_datetime = datetime.now()
    
    # 格式化当前时间信息
    current_date_str = current_datetime.strftime("%Y年%m月%d日")
    current_weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][current_datetime.weekday()]
    current_time_str = current_datetime.strftime("%H:%M")
    history_text = ""
    for msg in history:
        prefix = "用户：" if msg.get("role") == "user" else "AI："
        history_text += f"{prefix}{msg.get('content', '')}\n"

    knowledge_text = ""
    for k in knowledge_list:
        knowledge_text += f"【知识条目】标题：{k.title}\n内容：{k.content}\n\n"

    doctor_text = ""
    if recommended_doctors:
        # 检查是否有精确匹配的医生
        has_exact_match = any(d.get('is_exact_match', False) for d in recommended_doctors)
        
        if has_exact_match:
            doctor_text += "【系统精确匹配的推荐医生】（这些医生与您的描述高度匹配）：\n"
        else:
            doctor_text += "【候选医生列表】（请根据用户描述的症状和医生的专长信息，判断哪些医生适合，并推荐给用户）：\n"
        
        for i, d in enumerate(recommended_doctors, start=1):
            online_status = "（在线）" if d.get('is_online') else "（离线）"
            match_status = "（精确匹配）" if d.get('is_exact_match', False) else "（候选医生）"
            
            # 构建详细的医生信息
            doctor_info = f"{i}. 医生姓名：{d.get('name')}，职称：{d.get('title')}，所在机构：{d.get('department_name')}，在线状态：{online_status}{match_status}\n"
            
            # 添加专科信息
            if d.get('specialty'):
                doctor_info += f"   专科：{d.get('specialty')}\n"
            
            # 添加简介信息
            if d.get('introduction'):
                doctor_info += f"   简介：{d.get('introduction')}\n"
            
            # 添加经验信息
            if d.get('experience'):
                doctor_info += f"   经验：{d.get('experience')}\n"
            
            # 添加评分和评价数
            doctor_info += f"   评分：{d.get('score', 0):.1f}，评价数：{d.get('reviews', 0)}\n"
            
            doctor_text += doctor_info + "\n"
    else:
        doctor_text = "（暂未找到医生信息，只给出就诊建议即可，不要编造医生）"

    # 构建用户基本信息文本
    user_info_text = ""
    if extra_info:
        info_parts = []
        if extra_info.get('age'):
            age = extra_info['age']
            age_group = ""
            if age < 12:
                age_group = "（儿童，建议儿童口腔科）"
            elif age < 18:
                age_group = "（青少年，常见正畸需求）"
            elif age >= 60:
                age_group = "（老年人，可能涉及修复、种植等）"
            info_parts.append(f"年龄：{age}岁{age_group}")
        
        if extra_info.get('gender'):
            gender_text = "男" if extra_info['gender'] == 'male' else "女"
            info_parts.append(f"性别：{gender_text}")
        
        if extra_info.get('has_allergy'):
            info_parts.append("过敏史：有（需要特别注意药物过敏风险）")
        
        if info_parts:
            user_info_text = "\n".join(info_parts)

    prompt = f"""你是一名专业且谨慎的牙科智能助手。请根据下列信息，为用户提供科普性质的牙齿健康建议，并智能推荐合适的医生。

【当前日期时间】：今天是{current_date_str} {current_weekday}，当前时间是{current_time_str}。用户说"今天"指的是{current_date_str}，"明天"指的是{(current_datetime + timedelta(days=1)).strftime("%Y年%m月%d日")}。

【对话历史】：{history_text if history_text else "（无）"}

【用户本次提问】：{question}

{f'【用户基本信息】：{user_info_text}\n' if user_info_text else ''}

【相关牙科知识】：{knowledge_text if knowledge_text else "（未命中知识库，请结合常识谨慎回答）"}

【推荐医生列表】（**只能使用以下医生，不能编造任何医生信息**）：
{doctor_text}

**核心规则**：
1. 使用简明、口语化的中文，优先使用【相关牙科知识】中的内容。
2. 先客观解释可能涉及的牙科问题，但不要下诊断结论。
3. 根据用户描述直接推断就诊方向，不要说"如果...可能..."，直接说"根据您的描述，建议您..."。
4. **医生推荐规则（严格遵守）**：
   - 如果显示"【系统精确匹配的推荐医生】"，优先推荐这些医生。
   - 如果显示"【候选医生列表】"，根据专业匹配度选择：专科完全匹配 > 专科包含匹配 > 简介/经验匹配 > 评分。
   - 专业匹配规则："牙齿矫正/正畸"→正畸科；"口腔溃疡"→口腔内科/口腔黏膜科；"种植牙"→种植科；"龋齿/补牙"→口腔内科。
   - 只能推荐列表中的医生，使用真实姓名、职称、机构，不能编造。
   - 如果用户提到具体医生姓名，优先推荐该医生（如果在列表中）。
   - 如果候选医生专业不匹配，明确说"建议到XX科室就诊"，不要推荐专业不对口的医生。
   - 禁止使用"系统暂未提供"、"暂未找到"等否定性表述，直接推荐。
   - 如果没有医生列表，只能说"建议到XX科室就诊"，不能推荐具体医生。
5. 如有可能严重问题或急症风险，要明确提示用户尽快就医。
6. 不要提供处方药名和剂量，不要鼓励自行用药。
"""
    return prompt


