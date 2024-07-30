# Generated by Django 4.2.10 on 2024-03-06 14:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_test_thread_delete_generatedcontent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Task_thread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('thread_id', models.CharField(max_length=200)),
                ('assistant_id', models.CharField(max_length=200)),
                ('tasks_solved', models.IntegerField(default=0)),
                ('runs', models.IntegerField(default=0)),
                ('responses', models.JSONField(default=None)),
                ('prompts', models.JSONField(default=None)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.task')),
            ],
        ),
        migrations.DeleteModel(
            name='Test_thread',
        ),
    ]
