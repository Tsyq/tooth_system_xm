"""
AI问询视图
"""
import json
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from .models import Inquiry, AIChatMessage, AIRecommendationLog
from .serializers import (
    InquirySerializer,
    AIChatRequestSerializer,
    AIChatResponseSerializer,
)
from utils.response import success_response, error_response
from ai_inquiry.services.llm_client import call_llm, LLMCallError
from ai_inquiry.services.retrieval import (
    retrieve_knowledge_snippets,
    retrieve_doctors_by_intent,
)
from ai_inquiry.services.prompts import (
    build_intent_prompt,
    build_answer_prompt,
)


class InquiryViewSet(viewsets.ModelViewSet):
    """AI问询视图集（旧接口，保留兼容）"""
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """创建AI问询"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, '问询成功')


class AIChatView(APIView):
    """AI对话视图（核心接口）"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """处理AI对话请求"""
        serializer = AIChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        message = serializer.validated_data['message']
        extra_info = {
            "age": serializer.validated_data.get("age"),
            "gender": serializer.validated_data.get("gender"),
            "has_allergy": serializer.validated_data.get("has_allergy"),
        }
        
        # 1. 保存用户消息
        AIChatMessage.objects.create(
            user=user,
            role='user',
            content=message
        )
        
        # 2. 获取最近 N 条历史消息，用于上下文
        history_qs = AIChatMessage.objects.filter(user=user).order_by('-created_at')[:10]
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(history_qs)  # 转回时间正序
        ]
        
        # 3. 意图抽取（结构化 JSON）
        intent_prompt = build_intent_prompt(message, extra_info)
        try:
            intent_raw = call_llm(intent_prompt, temperature=0.0)
            try:
                intent = json.loads(intent_raw)
            except json.JSONDecodeError:
                # 如果返回的不是纯JSON，尝试提取JSON部分
                intent = {
                    "disease_category": "未知",
                    "recommended_department": None,
                    "priority_level": "info",
                }
        except LLMCallError as e:
            # 如果调用失败，使用默认意图
            intent = {
                "disease_category": "未知",
                "recommended_department": None,
                "priority_level": "info",
            }
        
        # 4. 检索知识库
        knowledge_list = retrieve_knowledge_snippets(message, limit=3)
        
        # 5. 根据意图推荐医生
        recommended_doctors = retrieve_doctors_by_intent(intent, limit=3)
        
        # 6. 构建最终回答 Prompt，调用大模型
        answer_prompt = build_answer_prompt(
            question=message,
            history=history,
            knowledge_list=knowledge_list,
            recommended_doctors=recommended_doctors,
        )
        
        try:
            answer = call_llm(answer_prompt, temperature=0.4)
        except LLMCallError as e:
            # 如果AI调用失败，返回友好的错误提示
            answer = f"抱歉，AI 服务暂时不可用，请稍后重试，或直接联系线下牙科医生就诊。（错误信息：{str(e)}）"
        
        # 7. 保存 AI 回复
        AIChatMessage.objects.create(
            user=user,
            role='assistant',
            content=answer
        )
        
        # 8. 保存推荐日志
        with transaction.atomic():
            AIRecommendationLog.objects.create(
                user=user,
                raw_question=message,
                structured_intent=intent,
                recommended_doctors=recommended_doctors,
            )
        
        # 9. 组装响应
        resp_data = {
            "answer": answer,
            "recommended_doctors": recommended_doctors,
            "suggestion_level": intent.get("priority_level", "info"),
        }
        resp_serializer = AIChatResponseSerializer(data=resp_data)
        resp_serializer.is_valid(raise_exception=True)
        
        return success_response(resp_serializer.data, '问询成功')


class AIChatHistoryView(ListAPIView):
    """AI对话历史视图"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """获取当前用户的对话历史"""
        user = request.user
        limit = int(request.query_params.get('limit', 20))
        
        qs = AIChatMessage.objects.filter(user=user).order_by('-created_at')[:limit]
        data = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in reversed(qs)  # 转回时间正序
        ]
        return success_response(data)

