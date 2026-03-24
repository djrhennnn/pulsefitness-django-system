from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone
import datetime


class UserProfile(models.Model):
    GENDER_CHOICES = [('male','Male'),('female','Female'),('other','Other')]
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age        = models.PositiveIntegerField(null=True, blank=True)
    gender     = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    height_cm  = models.FloatField(null=True, blank=True)
    weight_kg  = models.FloatField(null=True, blank=True)
    photo      = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s profile"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            return round(self.weight_kg / ((self.height_cm / 100) ** 2), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi is None:   return "Unknown"
        if bmi < 18.5:    return "Underweight"
        if bmi < 25:      return "Normal Weight"
        if bmi < 30:      return "Overweight"
        return "Obese"

    @property
    def avg_rating(self):
        result = self.client_ratings.aggregate(avg=Avg('stars'))['avg']
        return round(result, 1) if result else None

    @property
    def rating_count(self):
        return self.client_ratings.count()


class Trainer(models.Model):
    SPECIALTY_CHOICES = [
        ('strength',     'Strength / Powerlifting'),
        ('cardio',       'Cardio / HIIT'),
        ('bodybuilding', 'Bodybuilding'),
        ('yoga',         'Yoga & Mobility'),
    ]
    STATIC_PHOTOS = {
        "aron":   "fitness/images/aron.png",
        "justin": "fitness/images/jk.png",
        "jan":    "fitness/images/marcos.png",
        "marco":  "fitness/images/marcos.png",
        "rhen":   "fitness/images/rhen.png",
        "eto":    "fitness/images/eto.jpg",
    }
    user         = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='trainer_profile')
    name         = models.CharField(max_length=150)
    nickname     = models.CharField(max_length=100, blank=True)
    specialty    = models.CharField(max_length=30, choices=SPECIALTY_CHOICES)
    bio          = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    photo        = models.ImageField(upload_to='trainers/', null=True, blank=True)

    def __str__(self):
        return self.name

    def static_photo_key(self):
        first = self.name.split()[0].lower()
        return self.STATIC_PHOTOS.get(first, '')

    @property
    def avg_rating(self):
        result = self.ratings.aggregate(avg=Avg('stars'))['avg']
        return round(result, 1) if result else None

    @property
    def rating_count(self):
        return self.ratings.count()

    def get_booked_slots(self):
        sessions = ScheduledSession.objects.filter(
            trainer=self, booking__status__in=['confirmed', 'pending']
        ).values_list('session_date', 'session_time')
        return [{'date': str(d), 'time': str(t)[:5]} for d, t in sessions]


class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('expired',   'Expired'),
    ]
    member         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    trainer        = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='bookings')
    requested_at   = models.DateTimeField(auto_now_add=True)
    expires_at     = models.DateTimeField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes          = models.TextField(blank=True)
    total_sessions = models.PositiveIntegerField(default=1)
    sessions_done  = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.member.username} -> {self.trainer.name} ({self.status})"

    def check_and_expire(self):
        if self.status != 'pending':
            return False
        # Expire if earliest scheduled session date+time has passed
        sessions = self.scheduled_sessions.order_by('session_date', 'session_time')
        if sessions.exists():
            earliest = sessions.first()
            session_dt = timezone.make_aware(
                datetime.datetime.combine(earliest.session_date, earliest.session_time)
            )
            if timezone.now() > session_dt:
                self.status = 'expired'
                self.save(update_fields=['status'])
                return True
        # Fallback: expire after expires_at
        if self.expires_at and timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return True
        return False

    @property
    def sessions_remaining(self):
        return max(0, self.total_sessions - self.sessions_done)

    @property
    def is_sessions_exhausted(self):
        return self.sessions_done >= self.total_sessions


class TrainerRating(models.Model):
    booking    = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='trainer_rating')
    trainer    = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='ratings')
    member     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trainer_ratings_given')
    stars      = models.PositiveSmallIntegerField()
    comment    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'trainer')


class ClientRating(models.Model):
    booking    = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='client_rating')
    profile    = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='client_ratings')
    trainer    = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='client_ratings_given')
    stars      = models.PositiveSmallIntegerField()
    comment    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'profile')


class Message(models.Model):
    booking    = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body       = models.TextField(blank=True)
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)
    sent_at    = models.DateTimeField(auto_now_add=True)
    is_read    = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40] or '[voice]'}"


class WorkoutPlan(models.Model):
    booking    = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='workout_plans')
    trainer    = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='workout_plans')
    member     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_plans')
    title      = models.CharField(max_length=200)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WorkoutExercise(models.Model):
    plan         = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name='exercises')
    order        = models.PositiveIntegerField(default=1)
    name         = models.CharField(max_length=150)
    sets         = models.PositiveIntegerField(default=3)
    reps         = models.CharField(max_length=50, blank=True)
    duration_min = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['order']


class ScheduledSession(models.Model):
    booking      = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='scheduled_sessions')
    trainer      = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='scheduled_sessions')
    member       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_sessions')
    session_date = models.DateField()
    session_time = models.TimeField()
    duration_min = models.PositiveIntegerField(default=60)
    location     = models.CharField(max_length=200, blank=True, default='Gym Floor')
    notes        = models.TextField(blank=True)
    is_done      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['session_date', 'session_time']
