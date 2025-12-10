# Generated migration for adding visit_count field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hospitals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='hospital',
            name='visit_count',
            field=models.IntegerField(default=0, verbose_name='访问次数'),
        ),
        migrations.AddIndex(
            model_name='hospital',
            index=models.Index(fields=['-visit_count'], name='hospitals_h_visit_count_idx'),
        ),
    ]
