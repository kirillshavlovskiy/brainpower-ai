# Generated by Django 4.2.10 on 2024-07-23 20:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0022_filestructure'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filestructure',
            name='structure',
        ),
        migrations.AddField(
            model_name='filestructure',
            name='name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='filestructure',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='courses.filestructure'),
        ),
        migrations.AddField(
            model_name='filestructure',
            name='type',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='filestructure',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='file_structures', to=settings.AUTH_USER_MODEL),
        ),
    ]
