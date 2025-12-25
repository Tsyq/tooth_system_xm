from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('doctors', '0002_doctor_audit_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctor',
            name='hospital',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='doctors', to='hospitals.hospital'),
        ),
    ]
