from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('doctors', '0003_make_hospital_optional'),
    ]

    operations = [
        migrations.RenameField(
            model_name='doctor',
            old_name='approved_at',
            new_name='audited_at',
        ),
    ]
