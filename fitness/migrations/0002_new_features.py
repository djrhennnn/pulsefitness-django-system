from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0001_initial'),
    ]

    operations = [
        # Add sessions to BookingRequest + completed status
        migrations.AddField(
            model_name='bookingrequest',
            name='total_sessions',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='bookingrequest',
            name='sessions_done',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='bookingrequest',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'),
                         ('cancelled', 'Cancelled'), ('completed', 'Completed')],
                default='pending', max_length=20),
        ),
        # TrainerRating
        migrations.CreateModel(
            name='TrainerRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='trainer_rating', to='fitness.bookingrequest')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trainer_ratings_given', to='auth.user')),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='fitness.trainer')),
            ],
            options={'unique_together': {('booking', 'trainer')}},
        ),
        # ClientRating
        migrations.CreateModel(
            name='ClientRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='client_rating', to='fitness.bookingrequest')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_ratings', to='fitness.userprofile')),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_ratings_given', to='fitness.trainer')),
            ],
            options={'unique_together': {('booking', 'profile')}},
        ),
        # WorkoutPlan
        migrations.CreateModel(
            name='WorkoutPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workout_plans', to='fitness.bookingrequest')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workout_plans', to='auth.user')),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workout_plans', to='fitness.trainer')),
            ],
        ),
        # WorkoutExercise
        migrations.CreateModel(
            name='WorkoutExercise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=1)),
                ('name', models.CharField(max_length=150)),
                ('sets', models.PositiveIntegerField(default=3)),
                ('reps', models.CharField(blank=True, max_length=50)),
                ('duration_min', models.FloatField(blank=True, null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercises', to='fitness.workoutplan')),
            ],
            options={'ordering': ['order']},
        ),
    ]
