"""
AI问询视图
"""
import json
from datetime import datetime
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q

from .models import Inquiry, AIChatMessage, AIRecommendationLog
from .serializers import (
    InquirySerializer,
    AIChatRequestSerializer,
    AIChatResponseSerializer,
    AIChatMessageSerializer,
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
        
        # 5. 根据意图、问题和知识库内容智能推荐医生（不在检索阶段限制数量）
        recommended_doctors_all = retrieve_doctors_by_intent(
            intent=intent,
            question=message,
            knowledge_list=knowledge_list,
            limit=3  # 当前实现中已不再在函数内截断，仅作为兼容参数
        )

        # 基于上下文与历史推荐记录，过滤掉之前已经推荐过的医生
        # 这样用户追问“再推荐几个”时，可以优先给出新的医生
        from ai_inquiry.models import AIRecommendationLog

        # 当前意图的关键字段（用于区分不同就诊需求）
        cur_disease = intent.get("disease_category")
        cur_dept = intent.get("recommended_department")

        used_doctor_ids: set[int] = set()
        # 只看当前用户最近的一些推荐记录，且意图相同时才认为是“已经推荐过的医生”
        recent_logs = AIRecommendationLog.objects.filter(user=user).order_by("-created_at")[:20]
        for log in recent_logs:
            log_intent = log.structured_intent or {}
            if (
                isinstance(log_intent, dict)
                and log_intent.get("disease_category") == cur_disease
                and log_intent.get("recommended_department") == cur_dept
            ):
                docs = log.recommended_doctors or []
                for d in docs:
                    # 兼容两种形式：只存 id，或存完整字典
                    if isinstance(d, dict) and "id" in d:
                        used_doctor_ids.add(d["id"])
                    elif isinstance(d, int):
                        used_doctor_ids.add(d)

        # 过滤掉本意图下已经推荐过的医生
        filtered_doctors = [
            d for d in recommended_doctors_all
            if d.get("id") not in used_doctor_ids
        ]

        # 如果过滤后一个都没有，但原始结果非空，为了不让用户“什么医生都看不到”，退回原始结果
        if not filtered_doctors and recommended_doctors_all:
            recommended_doctors = recommended_doctors_all
        else:
            recommended_doctors = filtered_doctors
        
        # 6. 构建最终回答 Prompt，调用大模型
        # 获取当前时间，用于AI理解"今天"、"明天"等时间表达
        current_datetime = datetime.now()
        answer_prompt = build_answer_prompt(
            question=message,
            history=history,
            knowledge_list=knowledge_list,
            recommended_doctors=recommended_doctors,
            current_datetime=current_datetime,
        )
        
        try:
            # 使用system prompt强调规则，降低temperature提高准确性
            system_prompt = """你是一名专业的牙科智能助手。重要规则：
1. 关于医生推荐：只能使用系统提供的医生列表，绝对不能编造任何医生信息（包括姓名、职称、医院等）。
2. 如果系统没有推荐医生，只能说"建议到XX科室就诊"等通用建议，不能推荐任何具体医生。
3. 严格遵守系统提供的所有信息，不要添加、修改或编造任何内容。"""
            answer = call_llm(answer_prompt, system_prompt=system_prompt, temperature=0.3)
        except LLMCallError as e:
            # 如果AI调用失败，返回友好的错误提示
            answer = f"抱歉，AI 服务暂时不可用，请稍后重试，或直接联系线下牙科医生就诊。（错误信息：{str(e)}）"
        
        # 7. 从AI回答中提取实际推荐的医生（确保AI推荐的医生与返回给前端的列表一致）
        ai_recommended_doctors = []
        if recommended_doctors and answer:
            # 提取所有候选医生的姓名
            doctor_names = {d.get('name'): d for d in recommended_doctors if d.get('name')}
            
            # 从AI回答中查找提到的医生姓名
            # 使用更精确的匹配方式：检查医生姓名是否在回答中出现
            for name, doctor_info in doctor_names.items():
                # 检查AI回答中是否包含该医生姓名
                # 支持多种格式：姓名、姓名+医生、姓名+主任、姓名+医师、姓名+职称等
                name_patterns = [
                    name,  # 直接匹配姓名
                    f"{name}医生",
                    f"{name}主任",
                    f"{name}医师",
                    f"{name}大夫",
                    f"推荐{name}",
                    f"为您推荐{name}",
                    f"我为您推荐{name}",
                    f"推荐您{name}",
                ]
                
                # 检查是否匹配任何模式
                if any(pattern in answer for pattern in name_patterns):
                    ai_recommended_doctors.append(doctor_info)
            
            # 如果AI回答中没有找到任何医生，但系统有推荐医生，说明AI可能没有推荐
            # 此时返回空列表，前端就不会显示医生列表
            # 如果AI明确说"建议到XX科室就诊"等，也不返回医生列表
            if not ai_recommended_doctors:
                # 检查AI是否明确表示没有推荐医生
                no_recommendation_keywords = [
                    "暂未找到", "没有找到", "未找到", "暂未提供", "没有提供",
                    "建议到", "建议您到", "建议前往", "建议联系", "建议您联系",
                    "系统暂未", "系统没有", "没有特别匹配", "暂未找到匹配"
                ]
                # 如果AI回答中包含这些关键词，且没有提到具体医生姓名，则不返回医生列表
                has_no_recommendation = any(keyword in answer for keyword in no_recommendation_keywords)
                if has_no_recommendation:
                    # 检查是否提到了具体医生姓名（更严格的检查）
                    has_doctor_name = False
                    for name in doctor_names.keys():
                        if name in answer:
                            has_doctor_name = True
                            break
                    if not has_doctor_name:
                        ai_recommended_doctors = []  # 明确不推荐医生
        else:
            # 如果没有候选医生或AI回答为空，返回空列表
            ai_recommended_doctors = []
        
        # 8. 保存 AI 回复
        AIChatMessage.objects.create(
            user=user,
            role='assistant',
            content=answer
        )
        
        # 9. 保存推荐日志（保存AI实际推荐的医生）
        with transaction.atomic():
            AIRecommendationLog.objects.create(
                user=user,
                raw_question=message,
                structured_intent=intent,
                recommended_doctors=ai_recommended_doctors,  # 保存AI实际推荐的医生
            )
        
        # 10. 组装响应（只返回AI实际推荐的医生）
        resp_data = {
            "answer": answer,
            "recommended_doctors": ai_recommended_doctors,  # 只返回AI实际推荐的医生
            "suggestion_level": intent.get("priority_level", "info"),
        }
        resp_serializer = AIChatResponseSerializer(data=resp_data)
        resp_serializer.is_valid(raise_exception=True)
        
        return success_response(resp_serializer.data, '问询成功')


class AIChatHistoryView(APIView):
    """AI对话历史视图（分页加载，从最新消息开始）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        获取当前用户的对话历史（分页加载）
        从最新消息开始显示，向上滑动加载更早的消息
        
        支持参数：
        - page: 页码（默认1，第1页返回最新的消息）
        - page_size: 每页数量（默认20，最大100）
        
        使用说明：
        - page=1: 返回最新的20条消息（最新的在前）
        - page=2: 返回第21-40条消息（更早的消息）
        - 向上滑动时，前端应请求 page+1 来加载更早的消息
        """
        user = request.user
        
        # 获取查询集（按时间正序，最早的在前，方便前端从底部开始显示）
        queryset = AIChatMessage.objects.filter(user=user).order_by('created_at')
        
        # 分页参数处理
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        
        # 限制每页最大数量
        if page_size > 100:
            page_size = 100
        if page_size <= 0:
            page_size = 20
        if page <= 0:
            page = 1
        
        # 计算分页（从最新消息开始）
        total = queryset.count()
        
        if total == 0:
            # 没有消息
            messages = []
            total_pages = 0
            has_more = False
        else:
            # 计算总页数
            total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
            
            # 从最新消息开始分页（第1页显示最新的消息）
            # 例如：总共100条消息，每页20条
            # page=1: 显示第81-100条（最新的20条）
            # page=2: 显示第61-80条
            # page=5: 显示第1-20条（最早的20条）
            
            # 计算从后往前的索引
            start_index = max(0, total - page * page_size)
            end_index = total - (page - 1) * page_size
            
            # 如果 start_index >= end_index，说明请求的页码超出范围
            if start_index >= end_index:
                messages = []
                has_more = False
            else:
                messages = queryset[start_index:end_index]
                # 是否还有更早的消息（向上滑动时加载）
                has_more = page < total_pages
        
        serializer = AIChatMessageSerializer(messages, many=True)
        
        return success_response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,  # 正序：最早的在前，最新的在后（适合从底部显示）
            'has_more': has_more,  # 是否还有更早的消息（向上滑动加载）
            'total_pages': total_pages
        }, '获取成功')


class AIChatSearchView(APIView):
    """AI对话消息搜索视图（支持模糊搜索，按时间倒序）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        搜索当前用户的聊天记录
        支持参数：
        - keyword: 搜索关键词（必填，支持模糊匹配）
        - page: 页码（默认1）
        - page_size: 每页数量（默认20，最大100）
        
        返回结果按时间倒序（最新的在前），方便点击跳转到聊天页面
        """
        user = request.user
        
        # 获取搜索关键词
        keyword = request.query_params.get('keyword', '').strip()
        if not keyword:
            return error_response('搜索关键词不能为空', code=400)
        
        # 构建查询条件
        queryset = AIChatMessage.objects.filter(user=user)
        
        # 模糊搜索消息内容（使用icontains进行不区分大小写的模糊匹配）
        queryset = queryset.filter(content__icontains=keyword)
        
        # 按时间倒序排列（最新的在前）
        queryset = queryset.order_by('-created_at')
        
        # 分页处理
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        
        # 限制每页最大数量
        if page_size > 100:
            page_size = 100
        if page_size <= 0:
            page_size = 20
        if page <= 0:
            page = 1
        
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        messages = queryset[start:end]
        serializer = AIChatMessageSerializer(messages, many=True)
        
        return success_response({
            'keyword': keyword,
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,  # 按时间倒序，最新的在前
            'has_more': end < total,
            'total_pages': (total + page_size - 1) // page_size if page_size > 0 else 0
        }, '搜索成功')


class AIChatMessageLocationView(APIView):
    """AI对话消息定位视图（用于搜索后跳转到聊天页面）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, message_id):
        """
        根据消息ID获取该消息在聊天记录中的位置信息
        用于搜索后点击记录跳转到相应的聊天页面（类似微信的跳转功能）
        
        返回信息：
        - message_id: 消息ID
        - position: 该消息在所有消息中的位置（从1开始，按时间正序）
        - total_messages: 总消息数
        - page: 该消息所在的历史记录页码（基于历史记录分页逻辑，从最新消息开始）
        - context: 该消息的上下文信息（前后各3条消息，共7条）
        - message: 目标消息详情
        """
        user = request.user
        
        try:
            message = AIChatMessage.objects.get(id=message_id, user=user)
        except AIChatMessage.DoesNotExist:
            return error_response('消息不存在或无权限访问', code=404)
        
        # 获取该用户的所有消息（按时间正序）
        all_messages = AIChatMessage.objects.filter(user=user).order_by('created_at')
        total = all_messages.count()
        
        if total == 0:
            return error_response('没有消息记录', code=404)
        
        # 计算该消息在所有消息中的位置（从1开始，按时间正序）
        # 使用 annotate 和 count 来优化查询
        earlier_count = AIChatMessage.objects.filter(
            user=user,
            created_at__lt=message.created_at
        ).count()
        position = earlier_count + 1  # 从1开始计数
        
        # 计算该消息所在的历史记录页码（基于历史记录的分页逻辑）
        # 历史记录从最新消息开始分页，第1页显示最新的消息
        page_size = 20  # 使用默认分页大小
        
        # 从后往前计算页码
        # 例如：总共100条消息，position=100（最新的），应该在第1页
        # 例如：总共100条消息，position=20（第20条），应该在第5页
        from_back_position = total - position + 1  # 从后往前的位置
        page = (from_back_position + page_size - 1) // page_size if page_size > 0 else 1
        
        # 获取该消息的上下文（前后各3条消息，共7条）
        context_size = 3
        message_index = position - 1  # 转换为从0开始的索引
        
        start_index = max(0, message_index - context_size)
        end_index = min(total, message_index + context_size + 1)
        
        context_messages = all_messages[start_index:end_index]
        context_serializer = AIChatMessageSerializer(context_messages, many=True)
        
        return success_response({
            'message_id': message_id,
            'position': position,  # 在所有消息中的位置（从1开始，按时间正序）
            'total_messages': total,
            'page': page,  # 该消息所在的历史记录页码（从最新消息开始分页）
            'page_size': page_size,
            'context': context_serializer.data,  # 上下文消息（包含目标消息，按时间正序）
            'message': AIChatMessageSerializer(message).data  # 目标消息详情
        }, '获取成功')

