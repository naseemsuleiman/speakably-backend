# Generated by Django 4.2 on 2025-07-03 14:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0013_community'),
    ]

    operations = [
        migrations.AddField(
            model_name='communitypost',
            name='community',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='myapp.community'),
        ),
    ]
