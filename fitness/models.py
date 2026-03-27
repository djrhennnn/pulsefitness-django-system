from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg


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
        if bmi is None:          return "Unknown"
        if bmi < 18.5:           return "Underweight"
        if bmi < 25:             return "Normal Weight"
        if bmi < 30:             return "Overweight"
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

    user         = models.OneToOneField(User, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='trainer_profile')
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


class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('expired',   'Expired'),
    ]
    member           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    trainer          = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='bookings')
    requested_at     = models.DateTimeField(auto_now_add=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes            = models.TextField(blank=True)
    total_sessions   = models.PositiveIntegerField(default=1)
    sessions_done    = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"{self.member.username} -> {self.trainer.name} ({self.status})"

    @property
    def sessions_remaining(self):
        return max(0, self.total_sessions - self.sessions_done)

    @property
    def is_sessions_exhausted(self):
        return self.sessions_done >= self.total_sessions


class TrainerRating(models.Model):
    booking  = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='trainer_rating')
    trainer  = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='ratings')
    member   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trainer_ratings_given')
    stars    = models.PositiveSmallIntegerField()
    comment  = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'trainer')

    def __str__(self):
        return f"{self.member.username} rated {self.trainer.name}: {self.stars}star"


class ClientRating(models.Model):
    booking  = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='client_rating')
    profile  = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='client_ratings')
    trainer  = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='client_ratings_given')
    stars    = models.PositiveSmallIntegerField()
    comment  = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'profile')

    def __str__(self):
        return f"{self.trainer.name} rated {self.profile.user.username}: {self.stars}star"


class Message(models.Model):
    booking   = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='messages')
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body      = models.TextField()
    sent_at   = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"


class WorkoutPlan(models.Model):
    booking     = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='workout_plans')
    trainer     = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='workout_plans')
    member      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_plans')
    title       = models.CharField(max_length=200)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan for {self.member.username} by {self.trainer.name}"


class WorkoutExercise(models.Model):
    plan         = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name='exercises')
    order        = models.PositiveIntegerField(default=1)
    name         = models.CharField(max_length=150)
    sets         = models.PositiveIntegerField(default=3)
    reps         = models.CharField(max_length=50, blank=True)
    duration_min = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.sets}s x {self.reps})"


class ScheduledSession(models.Model):
    """A specific date/time slot that a trainer schedules for a booking."""
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

    def __str__(self):
        return f"{self.trainer.name} & {self.member.username} on {self.session_date} {self.session_time}"


class ProgressPost(models.Model):
    """Facebook-like progress post — any user (member or trainer) can post."""
    author      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_posts')
    caption     = models.TextField(blank=True)
    image       = models.ImageField(upload_to='progress/', null=True, blank=True)  # kept for backward compat
    created_at  = models.DateTimeField(auto_now_add=True)
    likes       = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    is_pinned   = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.author.username} — {self.created_at:%Y-%m-%d}"

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()


class ProgressPostImage(models.Model):
    """Multiple images per progress post."""
    post        = models.ForeignKey(ProgressPost, on_delete=models.CASCADE, related_name='images')
    image       = models.ImageField(upload_to='progress/')
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image {self.order} for post {self.post_id}"


class PostComment(models.Model):
    post        = models.ForeignKey(ProgressPost, on_delete=models.CASCADE, related_name='comments')
    author      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    body        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} on post {self.post_id}: {self.body[:40]}"


class SiteReview(models.Model):
    """Client reviews/ratings for the website itself, shown on the landing page."""
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='site_reviews')
    stars       = models.PositiveSmallIntegerField()  # 1–5
    comment     = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)  # admin can hide bad reviews

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.stars}★"
