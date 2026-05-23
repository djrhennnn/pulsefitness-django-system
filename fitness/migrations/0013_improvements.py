from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('fitness', '0012_analytics_models')]

    operations = [
        migrations.AlterField(
            model_name='userprofile', name='gender',
            field=models.CharField(blank=True, max_length=16, choices=[
                ('male','Male'),('female','Female'),
                ('other','Other'),('prefer_not','Prefer not to say')]),
        ),
        migrations.AddField(
            model_name='trainer', name='hourly_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='workoutexercise', name='video_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='workoutexercise', name='image_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.CreateModel(
            name='PostReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('reason', models.CharField(max_length=20, choices=[
                    ('spam','Spam or Advertising'),('inappropriate','Inappropriate Content'),
                    ('harassment','Harassment or Bullying'),('misinformation','Misinformation'),
                    ('other','Other')])),
                ('detail', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_reviewed', models.BooleanField(default=False)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='reports', to='fitness.progresspost')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='post_reports', to='auth.user')),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('post','reporter')}},
        ),
    ]
