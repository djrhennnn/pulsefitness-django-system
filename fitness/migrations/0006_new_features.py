from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0005_progresspost_postcomment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add is_pinned to ProgressPost
        migrations.AddField(
            model_name='progresspost',
            name='is_pinned',
            field=models.BooleanField(default=False),
        ),
        # Change ordering of ProgressPost
        migrations.AlterModelOptions(
            name='progresspost',
            options={'ordering': ['-is_pinned', '-created_at']},
        ),
        # Create ProgressPostImage
        migrations.CreateModel(
            name='ProgressPostImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='progress/')),
                ('order', models.PositiveIntegerField(default=0)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='fitness.progresspost')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        # Create SiteReview
        migrations.CreateModel(
            name='SiteReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_approved', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='site_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
