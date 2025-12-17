"""
Prompt 模板与构造工具。

包含两类 Prompt：
- 意图抽取：将自然语言描述转换为结构化 JSON（病症类别、推荐方向、紧急程度）；
- 回答生成：结合对话历史、知识库结果和推荐医生，生成最终中文回答。
"""
import json
from typing import Any, Dict, List

from ai_inquiry.models import DentalKnowledgeArticle


INTENT_EXTRACTION_SYSTEM_PROMPT = """
你是一个牙科分诊助手。请根据用户描述，提取结构化的就诊意图信息。
只输出合法 JSON，不要输出任何解释文字。

JSON 字段包括：
- "disease_category": 可能的病症类别（如：龋齿、牙髓炎、牙周炎、正畸需求 等，没有把握就填 "未知"）
- "recommended_department": 建议就诊的方向/专科名称（如：口腔内科、口腔外科、正畸科、儿童口腔科 等）
- "priority_level": "info"（仅咨询）、"normal"（建议就诊）、"urgent"（建议尽快就医）
"""


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
) -> str:
    """
    生成最终回答的 Prompt。

    history: [{"role": "user"/"assistant", "content": "..."}]
    """
    history_text = ""
    for msg in history:
        prefix = "用户：" if msg.get("role") == "user" else "AI："
        history_text += f"{prefix}{msg.get('content', '')}\n"

    knowledge_text = ""
    for k in knowledge_list:
        knowledge_text += f"【知识条目】标题：{k.title}\n内容：{k.content}\n\n"

    doctor_text = ""
    for i, d in enumerate(recommended_doctors, start=1):
        doctor_text += (
            f"{i}. 医生：{d.get('name')}（{d.get('title')}），所在机构：{d.get('department_name')}，"
            f"擅长：{d.get('good_at')}，最近可就诊时间：{d.get('next_available_time')}\n"
        )

    prompt = f"""
你是一名专业且谨慎的牙科智能助手。请根据下列信息，为用户提供科普性质的牙齿健康建议，并适当推荐就诊方向/医生。

【对话历史】（可能为空）：
{history_text}

【用户本次提问】：
{question}

【相关牙科知识】：
{knowledge_text if knowledge_text else "（未命中知识库，请结合常识谨慎回答）"}

【系统根据结构化意图筛选出的推荐医生】：
{doctor_text if doctor_text else "（暂未找到特别匹配的医生，只给出就诊建议即可）"}

回答要求：
1. 使用简明、口语化的中文。
2. 先客观解释可能涉及的牙科问题，但不要下诊断结论。
3. 给出是否需要线下就诊的建议，以及建议挂什么方向/专科、就诊时需要说明的情况。
4. 如有可能严重问题或急症风险，要明确提示用户尽快就医。
5. 不要提供处方药名和剂量，不要鼓励自行用药。
"""
    return prompt


