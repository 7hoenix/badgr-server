# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from mainsite.base import PopulateEntityIdsMigration


class Migration(migrations.Migration):

    dependencies = [
        ('issuer', '0019_auto_20170413_1136'),
    ]

    operations = [
        PopulateEntityIdsMigration('issuer', 'Issuer'),
        PopulateEntityIdsMigration('issuer', 'BadgeClass'),
        PopulateEntityIdsMigration('issuer', 'BadgeInstance', entity_class_name='Assertion'),
    ]



