# Generated manually to rename user relationship tables

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # 重命名 user_groups 表为 user_group
            sql="ALTER TABLE user_groups RENAME TO user_group;",
            reverse_sql="ALTER TABLE user_group RENAME TO user_groups;",
        ),
        migrations.RunSQL(
            # 重命名 user_user_permissions 表为 user_permission
            sql="ALTER TABLE user_user_permissions RENAME TO user_permission;",
            reverse_sql="ALTER TABLE user_permission RENAME TO user_user_permissions;",
        ),
    ]

