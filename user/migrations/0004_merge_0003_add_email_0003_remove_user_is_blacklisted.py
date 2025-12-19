from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0003_add_email'),
        ('user', '0003_remove_user_is_blacklisted'),
    ]

    operations = []
