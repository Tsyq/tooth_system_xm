from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='no_show_count',
            field=models.IntegerField(default=0, verbose_name='未按时签到次数'),
        ),
        migrations.AddField(
            model_name='user',
            name='is_blacklisted',
            field=models.BooleanField(default=False, verbose_name='是否拉黑'),
        ),
    ]
