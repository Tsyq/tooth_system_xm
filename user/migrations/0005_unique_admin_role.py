from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0004_merge_0003_add_email_0003_remove_user_is_blacklisted'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=['role'],
                condition=Q(role='admin'),
                name='unique_admin_role'
            ),
        ),
    ]
