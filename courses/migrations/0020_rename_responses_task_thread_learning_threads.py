# Generated by Django 4.2.10 on 2024-03-09 21:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0019_task_thread_prompts'),
    ]

    operations = [
        migrations.RenameField(
            model_name='task_thread',
            old_name='responses',
            new_name='learning_threads',
        ),
    ]
