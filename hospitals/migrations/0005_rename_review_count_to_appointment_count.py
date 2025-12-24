from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hospitals', '0004_remove_hospital_hospital_visit_c_b4bd25_idx_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='hospital',
            old_name='review_count',
            new_name='appointment_count',
        ),
        migrations.AlterModelOptions(
            name='hospital',
            options={'ordering': ['-appointment_count'], 'verbose_name': '医院', 'verbose_name_plural': '医院'},
        ),
    ]
