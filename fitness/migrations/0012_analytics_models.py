from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fitness', '0011_alter_message_body'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeightLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('weight_kg', models.FloatField()),
                ('logged_at', models.DateField(auto_now_add=True)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='weight_logs', to='auth.user')),
            ],
            options={'ordering': ['logged_at']},
        ),
        migrations.CreateModel(
            name='FitnessGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('goal_type', models.CharField(max_length=30, choices=[
                    ('lose_weight','Lose Weight'), ('gain_muscle','Gain Muscle'),
                    ('maintain_fitness','Maintain Fitness'), ('improve_cardio','Improve Cardio'),
                    ('increase_strength','Increase Strength'), ('flexibility','Improve Flexibility'),
                ])),
                ('target_weight', models.FloatField(blank=True, null=True)),
                ('target_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_achieved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='fitness_goals', to='auth.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
