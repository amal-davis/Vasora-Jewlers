# Generated by Django 4.2.5 on 2024-08-14 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vasoraapp', '0010_remove_order_subtotal'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
