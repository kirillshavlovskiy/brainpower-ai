# Generated by Django 3.2.9 on 2024-02-14 20:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_rename_prompt_generatedcontent_prompts'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generatedcontent',
            name='response',
        ),
    ]
