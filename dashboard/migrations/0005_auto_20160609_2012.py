# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-09 20:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_automationresult'),
    ]

    operations = [
        migrations.AlterField(
            model_name='automationresult',
            name='start_time',
            field=models.DateTimeField(),
        ),
    ]