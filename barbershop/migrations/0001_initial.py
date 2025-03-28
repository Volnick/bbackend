# Generated by Django 5.1.2 on 2025-01-29 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('is_booked', models.BooleanField(default=False)),
                ('customer_name', models.CharField(max_length=100)),
            ],
        ),
    ]
