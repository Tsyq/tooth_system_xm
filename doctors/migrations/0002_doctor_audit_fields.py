from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('doctors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='audit_status',
            field=models.CharField(
                verbose_name='审核状态', max_length=10,
                choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')],
                default='pending'
            ),
        ),
        migrations.AddField(
            model_name='doctor',
            name='applied_at',
            field=models.DateTimeField(verbose_name='申请时间', auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='doctor',
            name='approved_at',
            field=models.DateTimeField(verbose_name='通过时间', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='doctor',
            name='rejected_reason',
            field=models.CharField(verbose_name='拒绝原因', max_length=200, blank=True),
        ),
    ]
