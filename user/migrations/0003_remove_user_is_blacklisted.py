from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0002_user_blacklist_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_blacklisted',
        ),
    ]
