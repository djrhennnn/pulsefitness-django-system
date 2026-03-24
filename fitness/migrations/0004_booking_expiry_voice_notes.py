from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0003_scheduledsession'),
    ]

    operations = [
        # Add expires_at to BookingRequest
        migrations.AddField(
            model_name='bookingrequest',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Add 'expired' status choice
        migrations.AlterField(
            model_name='bookingrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('confirmed', 'Confirmed'),
                    ('cancelled', 'Cancelled'),
                    ('completed', 'Completed'),
                    ('expired', 'Expired'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        # Add voice_note to Message
        migrations.AddField(
            model_name='message',
            name='voice_note',
            field=models.FileField(blank=True, null=True, upload_to='voice_notes/'),
        ),
        # Make body optional (blank=True already, but ensure DB allows empty)
        migrations.AlterField(
            model_name='message',
            name='body',
            field=models.TextField(blank=True),
        ),
    ]
