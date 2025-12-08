"""
填充模拟数据的管理命令
使用方法: python manage.py fill_data
python manage.py fill_data --clear  # 清空现有数据后再填充
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random

from user.models import User
from hospitals.models import Hospital
from doctors.models import Doctor
from appointments.models import Appointment
from records.models import Record
from consultations.models import Consultation, Message
from ai_inquiry.models import Inquiry
from comment.models import Comment


class Command(BaseCommand):
    help = '填充数据库模拟数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空现有数据后再填充',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('正在清空现有数据...'))
            Comment.objects.all().delete()
            Inquiry.objects.all().delete()
            Message.objects.all().delete()
            Consultation.objects.all().delete()
            Record.objects.all().delete()
            Appointment.objects.all().delete()
            Doctor.objects.all().delete()
            Hospital.objects.all().delete()
            User.objects.filter(role__in=['user', 'doctor']).delete()
            self.stdout.write(self.style.SUCCESS('数据已清空'))

        self.stdout.write(self.style.SUCCESS('开始填充模拟数据...'))

        # 1. 创建用户
        users = self.create_users()
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(users)} 个用户'))

        # 2. 创建医院
        hospitals = self.create_hospitals()
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(hospitals)} 个医院'))

        # 3. 创建医生
        doctors = self.create_doctors(users, hospitals)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(doctors)} 个医生'))

        # 4. 创建预约
        appointments = self.create_appointments(users, doctors, hospitals)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(appointments)} 个预约'))

        # 5. 创建病历
        records = self.create_records(users, doctors, hospitals, appointments)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(records)} 个病历'))

        # 6. 创建问诊会话
        consultations = self.create_consultations(users, doctors)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(consultations)} 个问诊会话'))

        # 7. 创建消息
        messages = self.create_messages(consultations)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(messages)} 条消息'))

        # 8. 创建AI问询
        inquiries = self.create_inquiries(users)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(inquiries)} 个AI问询'))

        # 9. 创建评论
        comments = self.create_comments(users)
        self.stdout.write(self.style.SUCCESS(f'✓ 创建了 {len(comments)} 条评论'))

        self.stdout.write(self.style.SUCCESS('\n✅ 所有模拟数据填充完成！'))

    def create_users(self, count=30):
        """创建用户"""
        users = []
        first_names = ['张', '李', '王', '刘', '陈', '杨', '赵', '黄', '周', '吴', 
                       '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗']
        last_names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
                      '勇', '艳', '杰', '娟', '涛', '明', '超', '秀', '霞', '平']
        
        for i in range(count):
            phone = f'138{random.randint(10000000, 99999999)}'
            name = random.choice(first_names) + random.choice(last_names)
            role = random.choice(['user', 'user', 'user', 'doctor'])  # 大部分是普通用户
            
            user = User.objects.create_user(
                phone=phone,
                password='123456',  # 默认密码
                name=name,
                role=role,
                status=random.choice(['active', 'active', 'active', 'pending']),
                avatar=f'https://api.dicebear.com/7.x/avataaars/svg?seed={name}'
            )
            users.append(user)
        
        return users

    def create_hospitals(self, count=8):
        """创建医院"""
        hospitals = []
        hospital_names = [
            '北京口腔医院', '上海第九人民医院', '广州医科大学附属口腔医院',
            '四川大学华西口腔医院', '第四军医大学口腔医院', '武汉大学口腔医院',
            '北京大学口腔医院', '中山大学光华口腔医学院', '南京医科大学附属口腔医院',
            '重庆医科大学附属口腔医院', '山东大学口腔医院', '吉林大学口腔医院'
        ]
        
        addresses = [
            '北京市东城区天坛西里4号', '上海市黄浦区制造局路639号',
            '广州市越秀区陵园西路56号', '成都市武侯区人民南路三段14号',
            '西安市新城区长乐西路145号', '武汉市洪山区珞喻路237号',
            '北京市海淀区中关村南大街22号', '广州市越秀区陵园西路56号',
            '南京市鼓楼区汉中路136号', '重庆市渝北区松石北路426号',
            '济南市历下区文化西路44-1号', '长春市朝阳区清华路1500号'
        ]
        
        for i in range(min(count, len(hospital_names))):
            hospital = Hospital.objects.create(
                name=hospital_names[i],
                address=addresses[i] if i < len(addresses) else f'地址{i+1}',
                phone=f'0{random.randint(100, 999)}-{random.randint(10000000, 99999999)}',
                latitude=round(random.uniform(30, 40), 6),
                longitude=round(random.uniform(110, 120), 6),
                rating=round(random.uniform(3.5, 5.0), 1),
                review_count=random.randint(50, 500),
                description=f'{hospital_names[i]}是一所集医疗、教学、科研为一体的三级甲等口腔专科医院。',
                business_hours='08:00-17:30',
                image=f'https://picsum.photos/400/300?random={i}'
            )
            hospitals.append(hospital)
        
        return hospitals

    def create_doctors(self, users, hospitals):
        """创建医生"""
        doctors = []
        doctor_users = [u for u in users if u.role == 'doctor']
        
        # 如果医生用户不够，创建更多
        if len(doctor_users) < 15:
            for i in range(15 - len(doctor_users)):
                phone = f'139{random.randint(10000000, 99999999)}'
                name = random.choice(['张', '李', '王', '刘', '陈']) + random.choice(['伟', '强', '军', '勇', '杰'])
                user = User.objects.create_user(
                    phone=phone,
                    password='123456',
                    name=name,
                    role='doctor',
                    status='active'
                )
                doctor_users.append(user)
        
        titles = ['主任医师', '副主任医师', '主治医师', '住院医师']
        specialties = ['口腔内科', '口腔外科', '口腔修复', '口腔正畸', '口腔种植', '儿童口腔', '牙周病', '牙体牙髓']
        
        for i, user in enumerate(doctor_users[:20]):  # 最多20个医生
            hospital = random.choice(hospitals)
            doctor = Doctor.objects.create(
                user=user,
                name=user.name,
                title=random.choice(titles),
                specialty=random.choice(specialties),
                hospital=hospital,
                score=round(random.uniform(4.0, 5.0), 1),
                reviews=random.randint(10, 200),
                introduction=f'{user.name}，{random.choice(titles)}，擅长{random.choice(specialties)}相关疾病的诊治。',
                education=random.choice(['本科', '硕士', '博士']),
                experience=f'从事口腔医学工作{random.randint(5, 30)}年',
                is_online=random.choice([True, True, False]),  # 大部分在线
                is_admin=random.choice([True, False, False, False])  # 少数是管理员
            )
            doctors.append(doctor)
        
        return doctors

    def create_appointments(self, users, doctors, hospitals, count=50):
        """创建预约"""
        appointments = []
        statuses = ['upcoming', 'completed', 'cancelled', 'checked-in']
        times = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00']
        
        regular_users = [u for u in users if u.role == 'user']
        
        for i in range(count):
            user = random.choice(regular_users)
            doctor = random.choice(doctors)
            hospital = doctor.hospital
            
            # 随机日期（过去30天到未来30天）
            days_offset = random.randint(-30, 30)
            appointment_date = timezone.now().date() + timedelta(days=days_offset)
            appointment_time = random.choice(times)
            status = random.choice(statuses)
            
            # 检查时间冲突（简化处理，实际应该更严格）
            existing = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time
            ).exists()
            
            if not existing:
                appointment = Appointment.objects.create(
                    user=user,
                    doctor=doctor,
                    hospital=hospital,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    symptoms=random.choice([
                        '牙齿疼痛', '牙龈出血', '牙齿松动', '口腔异味',
                        '需要洗牙', '牙齿矫正咨询', '种植牙咨询', '补牙'
                    ]),
                    patient_name=user.name,
                    patient_phone=user.phone,
                    status=status,
                    checkin_time=timezone.now() - timedelta(hours=random.randint(1, 24)) if status == 'checked-in' else None
                )
                appointments.append(appointment)
        
        return appointments

    def create_records(self, users, doctors, hospitals, appointments, count=40):
        """创建病历"""
        records = []
        regular_users = [u for u in users if u.role == 'user']
        diagnoses = [
            '龋齿', '牙周炎', '根尖周炎', '牙髓炎', '智齿冠周炎',
            '牙列不齐', '牙齿缺失', '牙体缺损', '口腔溃疡', '牙龈炎'
        ]
        treatments = [
            '根管治疗', '补牙', '拔牙', '洗牙', '正畸治疗',
            '种植牙', '烤瓷牙', '全瓷牙', '牙周治疗', '药物治疗'
        ]
        medications_list = [
            ['阿莫西林', '布洛芬'],
            ['头孢克肟', '甲硝唑'],
            ['阿莫西林', '奥硝唑'],
            ['布洛芬', '甲硝唑'],
            ['头孢拉定', '对乙酰氨基酚']
        ]
        
        for i in range(count):
            user = random.choice(regular_users)
            doctor = random.choice(doctors)
            hospital = doctor.hospital
            appointment = random.choice(appointments) if appointments and random.choice([True, False]) else None
            
            days_offset = random.randint(-60, 0)
            date = timezone.now().date() + timedelta(days=days_offset)
            
            record = Record.objects.create(
                user=user,
                doctor=doctor,
                hospital=hospital,
                appointment=appointment,
                date=date,
                diagnosis=random.choice(diagnoses),
                content=f'患者主诉{random.choice(["牙齿疼痛", "牙龈出血", "牙齿松动"])}，检查发现{random.choice(diagnoses)}，建议{random.choice(treatments)}。',
                treatment=random.choice(treatments),
                medications=random.choice(medications_list),
                rated=random.choice([True, False]),
                rating=random.randint(3, 5) if random.choice([True, False]) else None,
                comment=random.choice([
                    '医生很专业，治疗效果很好',
                    '服务态度很好，很满意',
                    '治疗效果不错，推荐',
                    '医生很耐心，解释很详细'
                ]) if random.choice([True, False]) else None
            )
            records.append(record)
        
        return records

    def create_consultations(self, users, doctors, count=25):
        """创建问诊会话"""
        consultations = []
        regular_users = [u for u in users if u.role == 'user']
        
        for i in range(count):
            user = random.choice(regular_users)
            doctor = random.choice(doctors)
            status = random.choice(['active', 'closed', 'closed'])
            
            consultation = Consultation.objects.create(
                user=user,
                doctor=doctor,
                status=status
            )
            consultations.append(consultation)
        
        return consultations

    def create_messages(self, consultations, count=100):
        """创建消息"""
        messages = []
        message_templates = [
            '您好，我想咨询一下牙齿疼痛的问题',
            '我的牙齿最近总是出血，是什么原因？',
            '请问种植牙需要多长时间？',
            '洗牙会不会很疼？',
            '我的智齿需要拔掉吗？',
            '牙齿矫正大概需要多长时间？',
            '好的，我了解了，谢谢医生',
            '我会按照您的建议去做的',
            '建议您先拍个片子看看具体情况',
            '这种情况需要及时治疗，建议尽快就诊',
            '可以先吃点消炎药缓解一下',
            '建议您定期复查，注意口腔卫生'
        ]
        
        for i in range(count):
            consultation = random.choice(consultations)
            sender = random.choice(['user', 'doctor'])
            text = random.choice(message_templates)
            
            # 随机时间（会话创建时间之后）
            time_offset = random.randint(0, 3600 * 24 * 7)  # 7天内
            message_time = consultation.created_at + timedelta(seconds=time_offset)
            
            message = Message(
                consultation=consultation,
                sender=sender,
                text=text
            )
            message.save()
            # 更新time字段（因为auto_now_add只在创建时设置）
            Message.objects.filter(id=message.id).update(time=message_time)
            message.refresh_from_db()
            messages.append(message)
        
        return messages

    def create_inquiries(self, users, count=30):
        """创建AI问询"""
        inquiries = []
        regular_users = [u for u in users if u.role == 'user']
        
        questions = [
            '牙齿疼痛怎么办？',
            '牙龈出血是什么原因？',
            '智齿需要拔掉吗？',
            '洗牙对牙齿有伤害吗？',
            '牙齿矫正的最佳年龄是多少？',
            '种植牙能用多久？',
            '如何预防龋齿？',
            '牙齿敏感是什么原因？',
            '口臭怎么治疗？',
            '儿童几岁开始刷牙？'
        ]
        
        answers = [
            '牙齿疼痛可能是龋齿、牙髓炎等原因，建议及时就医检查。',
            '牙龈出血通常是牙周炎或牙龈炎的表现，需要及时治疗。',
            '智齿如果位置不正、反复发炎，建议拔除。',
            '洗牙是安全的，定期洗牙有助于维护口腔健康。',
            '牙齿矫正没有严格的年龄限制，但青少年时期效果更好。',
            '种植牙在良好维护下可以使用10-20年甚至更久。',
            '预防龋齿需要保持良好的口腔卫生，定期检查。',
            '牙齿敏感可能是牙本质暴露，建议使用抗敏感牙膏。',
            '口臭可能与口腔疾病、消化系统疾病有关，需要查明原因。',
            '儿童从第一颗牙萌出就应该开始刷牙，家长要帮助和监督。'
        ]
        
        suggestions_list = [
            ['及时就医', '注意口腔卫生', '避免冷热刺激'],
            ['定期洗牙', '使用牙线', '戒烟限酒'],
            ['拍片检查', '咨询专业医生', '注意口腔卫生'],
            ['定期洗牙', '正确刷牙', '使用漱口水'],
            ['咨询正畸医生', '拍片检查', '制定治疗方案'],
            ['选择正规医院', '做好术后护理', '定期复查'],
            ['正确刷牙', '使用含氟牙膏', '定期检查'],
            ['使用抗敏感牙膏', '避免冷热刺激', '咨询医生'],
            ['检查口腔疾病', '注意饮食', '保持口腔卫生'],
            ['使用儿童牙刷', '使用含氟牙膏', '家长监督']
        ]
        
        for i in range(count):
            user = random.choice(regular_users)
            question = random.choice(questions)
            answer = random.choice(answers)
            suggestions = random.choice(suggestions_list)
            
            inquiry = Inquiry.objects.create(
                user=user,
                question=question,
                answer=answer,
                suggestions=suggestions
            )
            inquiries.append(inquiry)
        
        return inquiries

    def create_comments(self, users, count=20):
        """创建评论"""
        comments = []
        regular_users = [u for u in users if u.role == 'user']
        
        comment_texts = [
            '服务很好，医生很专业',
            '治疗效果不错，很满意',
            '医院环境很好，设备先进',
            '医生很耐心，解释很详细',
            '预约很方便，就诊流程顺畅',
            '价格合理，服务周到',
            '医生技术很好，推荐',
            '整体体验不错，会推荐给朋友',
            '医院位置方便，停车方便',
            '医护人员态度很好'
        ]
        
        for i in range(count):
            user = random.choice(regular_users)
            text = random.choice(comment_texts)
            
            comment = Comment.objects.create(
                user=user,
                text=text
            )
            comments.append(comment)
        
        return comments

