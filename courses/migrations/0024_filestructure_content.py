# Generated by Django 4.2.10 on 2024-07-24 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0023_remove_filestructure_structure_filestructure_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='filestructure',
            name='content',
            field=models.TextField(blank=True, null=True),
        ),
    ]
