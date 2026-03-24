#!/usr/bin/env python
"""
Run once to set up the database:
    python setup.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulse.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from fitness.models import Trainer, UserProfile

print("Running migrations...")
call_command('migrate', verbosity=0)

print("Creating trainers...")
TRAINER_DATA = [
    dict(name="Aron 'The Destroyer' Jay",   specialty='strength',
         bio='Specialist in strength training and powerlifting. 10+ years experience.',
         email='aron@pulse.com',   password='aron1234'),
    dict(name="Justin 'The Smasher' Kerby", specialty='cardio',
         bio='High-intensity interval training and metabolic conditioning expert.',
         email='justin@pulse.com', password='justin1234'),
    dict(name="Jan 'Muscle Man' Marco",     specialty='bodybuilding',
         bio='Bodybuilding coach focused on hypertrophy and aesthetics.',
         email='marco@pulse.com',  password='marco1234'),
    dict(name="Rhen 'Eruption' Lewis",      specialty='yoga',
         bio='Yoga instructor and mobility specialist for recovery.',
         email='rhen@pulse.com',   password='rhen1234'),
]

for td in TRAINER_DATA:
    email    = td.pop('email')
    password = td.pop('password')
    user, created = User.objects.get_or_create(
        username=email,
        defaults=dict(email=email, first_name=td['name'].split()[0],
                      is_staff=False, is_superuser=False)
    )
    if created:
        user.set_password(password)
        user.save()
    trainer, _ = Trainer.objects.get_or_create(name=td['name'], defaults={**td, 'user': user})
    if trainer.user is None:
        trainer.user = user
        trainer.save()
    print(f"  ✓ {td['name']}  →  {email} / {password}")

print("Creating admin...")
if not User.objects.filter(username='admin@pulse.com').exists():
    User.objects.create_superuser('admin@pulse.com', 'admin@pulse.com', 'admin1234', first_name='Admin')
    print("  ✓ admin@pulse.com / admin1234")
else:
    print("  ✓ admin@pulse.com already exists")

print("""
╔══════════════════════════════════════════════════════════╗
║  Setup complete! Run: python manage.py runserver         ║
║  Open: http://127.0.0.1:8000/                            ║
╠══════════════════════════════════════════════════════════╣
║  ADMIN      admin@pulse.com    / admin1234               ║
║  TRAINER 1  aron@pulse.com     / aron1234                ║
║  TRAINER 2  justin@pulse.com   / justin1234              ║
║  TRAINER 3  marco@pulse.com    / marco1234               ║
║  TRAINER 4  rhen@pulse.com     / rhen1234                ║
║  MEMBERS    register on site                             ║
╚══════════════════════════════════════════════════════════╝
""")
