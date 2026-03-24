from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0002_new_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_date', models.DateField()),
                ('session_time', models.TimeField()),
                ('duration_min', models.PositiveIntegerField(default=60)),
                ('location', models.CharField(blank=True, default='Gym Floor', max_length=200)),
                ('notes', models.TextField(blank=True)),
                ('is_done', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_sessions', to='fitness.bookingrequest')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_sessions', to='auth.user')),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_sessions', to='fitness.trainer')),
            ],
            options={'ordering': ['session_date', 'session_time']},
        ),
    ]
