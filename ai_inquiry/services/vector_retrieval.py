"""
向量检索服务（方案一：语义检索）
使用文本向量模型进行语义相似度搜索
"""
import numpy as np
from typing import List, Optional
from django.conf import settings

from ai_inquiry.models import DentalKnowledgeArticle


# 全局变量：存储模型实例（避免重复加载）
_embedding_model = None


def get_embedding_model():
    """获取或初始化embedding模型（懒加载）"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import os
            
            # 设置Hugging Face镜像（sentence-transformers使用huggingface_hub）
            # 注意：huggingface_hub使用HF_ENDPOINT环境变量，但需要设置完整的URL
            hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
            os.environ["HF_ENDPOINT"] = hf_endpoint
            
            # 同时设置HF_HUB_CACHE，避免重复下载
            if "HF_HUB_CACHE" not in os.environ:
                import tempfile
                cache_dir = os.path.join(tempfile.gettempdir(), "hf_cache")
                os.environ["HF_HUB_CACHE"] = cache_dir
            
            # 设置超时，避免首次下载时卡住
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            
            try:
                _embedding_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2',
                    cache_folder=os.environ.get("HF_HUB_CACHE")
                )
            except Exception:
                try:
                    _embedding_model = SentenceTransformer(
                        'all-MiniLM-L6-v2',
                        cache_folder=os.environ.get("HF_HUB_CACHE")
                    )
                except Exception:
                    return None
            finally:
                socket.setdefaulttimeout(original_timeout)
        except ImportError:
            return None
    return _embedding_model


def generate_embedding(text: str) -> List[float]:
    """
    为文本生成向量
    
    Args:
        text: 输入文本
        
    Returns:
        向量列表（浮点数列表）
    """
    model = get_embedding_model()
    # 生成向量（返回numpy数组，转换为列表）
    vector = model.encode(text, convert_to_numpy=True)
    return vector.tolist()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    
    Args:
        vec1: 向量1
        vec2: 向量2
        
    Returns:
        相似度分数（0-1之间）
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    # 计算余弦相似度
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def retrieve_knowledge_by_vector(
    question: str,
    limit: int = 3,
    similarity_threshold: float = 0.3,
    max_articles: int = 200  # 限制最多检索的文章数量，避免性能问题
) -> List[DentalKnowledgeArticle]:
    """
    使用向量检索相关知识文章（语义检索）
    
    Args:
        question: 用户问题
        limit: 返回结果数量
        similarity_threshold: 相似度阈值，低于此值的结果将被过滤
        max_articles: 最多检索的文章数量，超过此数量会限制范围（性能优化）
        
    Returns:
        相关知识文章列表，按相似度降序排列
    """
    import time
    start_time = time.time()
    
    # 1. 生成问题的向量
    try:
        model = get_embedding_model()
        if model is None:
            return []
        question_vector = generate_embedding(question)
        question_vec = np.array(question_vector)
    except Exception:
        return []
    
    # 2. 获取所有启用的知识文章（只获取有向量的文章）
    # 性能优化：限制检索范围，避免遍历过多文章
    articles_qs = DentalKnowledgeArticle.objects.filter(
        is_active=True,
        embedding__isnull=False
    )
    
    total_count = articles_qs.count()
    if total_count == 0:
        # 如果没有向量化的文章，返回空列表
        return []
    
    # 如果文章数量太多，限制检索范围（优先检索最近更新的文章）
    if total_count > max_articles:
        articles_qs = articles_qs.order_by('-updated_at', '-id')[:max_articles]
        print(f"向量检索：文章总数 {total_count}，限制检索前 {max_articles} 篇（按更新时间排序）")
    
    # 批量获取文章和向量（避免逐个查询数据库）
    articles = list(articles_qs)
    
    if not articles:
        return []
    
    # 3. 批量计算相似度（使用numpy向量化计算，大幅提升性能）
    # 先提取所有文章的向量（在try外部，确保异常处理时可用）
    article_vectors = []
    valid_articles = []
    
    for article in articles:
        if article.embedding:
            article_vectors.append(article.embedding)
            valid_articles.append(article)
    
    if not article_vectors:
        return []
    
    try:
        # 转换为numpy数组（批量计算）
        article_vecs = np.array(article_vectors)
        
        # 批量计算余弦相似度（向量化操作，比循环快几十倍）
        # 计算点积
        dot_products = np.dot(article_vecs, question_vec)
        
        # 计算范数
        article_norms = np.linalg.norm(article_vecs, axis=1)
        question_norm = np.linalg.norm(question_vec)
        
        # 避免除零
        norms = article_norms * question_norm
        norms = np.where(norms == 0, 1, norms)  # 如果范数为0，设为1避免除零
        
        # 计算相似度
        similarities = dot_products / norms
        
        # 4. 过滤和排序
        results = []
        for i, similarity in enumerate(similarities):
            # 只保留相似度高于阈值的结果
            if similarity >= similarity_threshold:
                results.append((valid_articles[i], float(similarity)))
        
        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 返回前limit个结果
        return [article for article, _ in results[:limit]]
        
    except Exception as e:
        # 如果批量计算失败，回退到逐个计算（但限制数量）
        results = []
        # 限制数量，避免性能问题
        for article in valid_articles[:max_articles]:
            if not article.embedding:
                continue
            
            # 计算相似度
            similarity = cosine_similarity(question_vector, article.embedding)
            
            # 只保留相似度高于阈值的结果
            if similarity >= similarity_threshold:
                results.append((article, similarity))
        
        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个结果
        return [article for article, _ in results[:limit]]


def batch_generate_embeddings(articles: Optional[List[DentalKnowledgeArticle]] = None):
    """
    批量生成知识文章的向量（用于初始化）
    
    Args:
        articles: 要生成向量的文章列表，如果为None则处理所有文章
    """
    if articles is None:
        articles = DentalKnowledgeArticle.objects.filter(is_active=True)
    
    model = get_embedding_model()
    
    # 准备文本列表
    texts = []
    article_list = list(articles)
    
    for article in article_list:
        # 组合标题和内容作为文本
        text = f"{article.title} {article.content}"
        if article.tags:
            text += f" {article.tags}"
        texts.append(text)
    
    if not texts:
        return
    
    # 批量生成向量
    try:
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        
        # 保存向量到数据库
        for i, article in enumerate(article_list):
            article.embedding = vectors[i].tolist()
            article.save(update_fields=['embedding'])
        
        print(f"成功为 {len(article_list)} 篇文章生成向量")
    except Exception as e:
        print(f"批量生成向量失败: {e}")
        raise

