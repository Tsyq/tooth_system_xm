"""
管理命令：为知识库文章生成向量
使用方法：python manage.py generate_embeddings
"""
from django.core.management.base import BaseCommand
from ai_inquiry.models import DentalKnowledgeArticle
from ai_inquiry.services.vector_retrieval import batch_generate_embeddings


class Command(BaseCommand):
    help = '为知识库文章生成向量（用于语义检索）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='为所有文章生成向量（包括已生成的）',
        )
        parser.add_argument(
            '--article-ids',
            nargs='+',
            type=int,
            help='指定要生成向量的文章ID列表',
        )

    def handle(self, *args, **options):
        self.stdout.write('开始生成向量...')
        
        if options['article_ids']:
            # 为指定的文章生成向量
            articles = DentalKnowledgeArticle.objects.filter(
                id__in=options['article_ids'],
                is_active=True
            )
            self.stdout.write(f'为 {articles.count()} 篇指定文章生成向量...')
        elif options['all']:
            # 为所有文章生成向量
            articles = DentalKnowledgeArticle.objects.filter(is_active=True)
            self.stdout.write(f'为所有 {articles.count()} 篇文章生成向量...')
        else:
            # 只为还没有向量的文章生成向量
            articles = DentalKnowledgeArticle.objects.filter(
                is_active=True,
                embedding__isnull=True
            )
            self.stdout.write(f'为 {articles.count()} 篇未生成向量的文章生成向量...')
        
        if not articles.exists():
            self.stdout.write(self.style.WARNING('没有需要生成向量的文章'))
            return
        
        try:
            batch_generate_embeddings(articles)
            self.stdout.write(self.style.SUCCESS(f'成功为 {articles.count()} 篇文章生成向量'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'生成向量失败: {e}'))
            raise

