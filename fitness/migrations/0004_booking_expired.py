from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0003_scheduledsession'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending',   'Pending'),
                    ('confirmed', 'Confirmed'),
                    ('cancelled', 'Cancelled'),
                    ('completed', 'Completed'),
                    ('expired',   'Expired'),
                ],
                default='pending', max_length=20),
        ),
    ]
