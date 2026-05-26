from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
import json

from .models import (UserProfile, Trainer, BookingRequest, Message,
                     TrainerRating, ClientRating, WorkoutPlan, WorkoutExercise,
                     ScheduledSession, ProgressPost, ProgressPostImage, PostComment, SiteReview,
                     WeightLog, FitnessGoal, PostReport)
from django.db.models import Count, Avg, Sum, Q
from datetime import date, timedelta


# ── Role helpers ──────────────────────────────────────────

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def is_trainer(user):
    if not user.is_authenticated or user.is_superuser:
        return False
    return Trainer.objects.filter(user=user).exists()

def get_trainer_for_user(user):
    try:
        return user.trainer_profile
    except Trainer.DoesNotExist:
        return None

def _landing_ctx(extra=None):
    from django.db.models import Avg as _Avg
    trainers = Trainer.objects.all()
    try:
        site_reviews = SiteReview.objects.filter(is_approved=True).select_related('user').order_by('-created_at')[:20]
        avg_val = SiteReview.objects.filter(is_approved=True).aggregate(avg=_Avg('stars'))['avg']
        avg_site_rating = round(avg_val, 1) if avg_val else None
    except Exception:
        site_reviews = []
        avg_site_rating = None
    ctx = {'trainers': trainers, 'site_reviews': site_reviews, 'avg_site_rating': avg_site_rating}
    if extra:
        ctx.update(extra)
    return ctx


# ── Home ──────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        if is_admin(request.user):    return redirect('admin_dashboard')
        if is_trainer(request.user):  return redirect('trainer_dashboard')
        return redirect('member_dashboard')
    return render(request, 'fitness/lenux.html', _landing_ctx())


# ── Register ──────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        age      = request.POST.get('age', '').strip()
        gender   = request.POST.get('gender', '')
        height   = ''
        weight   = ''

        def fail(msg):
            return render(request, 'fitness/lenux.html', _landing_ctx({
                'open_modal': 'register', 'register_error': msg,
                'reg_name': name, 'reg_email': email, 'reg_age': age,
                'reg_gender': gender, 'reg_height': height, 'reg_weight': weight,
            }))

        if not all([name, email, password]):
            return fail('Name, email, and password are required.')
        if len(password) < 8:
            return fail('Password must be at least 8 characters.')
        if User.objects.filter(username=email).exists():
            return fail('An account with that email already exists.')

        parts = name.split()
        try:
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=parts[0],
                last_name=' '.join(parts[1:]) if len(parts) > 1 else '',
            )
        except IntegrityError:
            return fail('An account with that email already exists.')

        UserProfile.objects.get_or_create(user=user, defaults={
            'age': int(age) if age.isdigit() else None,
            'gender': gender,
            'height_cm': float(height) if height else None,
            'weight_kg': float(weight) if weight else None,
        })
        login(request, user)
        return redirect('member_dashboard')
    return redirect('home')


# ── Login / Logout ────────────────────────────────────────

def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if is_admin(user):   return redirect('admin_dashboard')
            if is_trainer(user): return redirect('trainer_dashboard')
            return redirect('member_dashboard')
        return render(request, 'fitness/lenux.html', _landing_ctx({
            'open_modal': 'login',
            'login_error': 'Invalid email or password.',
            'login_email': email,
        }))
    return redirect('home')

def user_logout(request):
    logout(request)
    return redirect('home')


# ── Member Dashboard ──────────────────────────────────────

@login_required(login_url='/')
def member_dashboard(request):
    if is_admin(request.user):   return redirect('admin_dashboard')
    if is_trainer(request.user): return redirect('trainer_dashboard')
    expire_pending_bookings()

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    trainers   = Trainer.objects.all()
    bookings   = BookingRequest.objects.filter(
        member=request.user).select_related('trainer').order_by('-requested_at')

    unread = Message.objects.filter(
        booking__member=request.user, is_read=False
    ).exclude(sender=request.user).count()

    # bookings that need rating (sessions exhausted or cancelled, no rating yet)
    pending_rate_trainer = []
    try:
        for b in bookings:
            if b.status in ('completed', 'cancelled', 'expired'):
                if not TrainerRating.objects.filter(booking=b).exists():
                    pending_rate_trainer.append(b)
    except Exception:
        pending_rate_trainer = []

    # workout plans for this member
    try:
        workout_plans = WorkoutPlan.objects.filter(
            member=request.user).select_related('trainer', 'booking').prefetch_related('exercises').order_by('-created_at')
    except Exception:
        workout_plans = []

    # client ratings for this member (shown to next trainers)
    try:
        my_client_ratings = ClientRating.objects.filter(
            profile__user=request.user
        ).select_related('trainer', 'booking').order_by('-created_at')
    except Exception:
        my_client_ratings = []

    # user's existing site review (if any)
    try:
        my_site_review = request.user.site_reviews
    except SiteReview.DoesNotExist:
        my_site_review = None
    except Exception:
        my_site_review = None

    context = {
        'profile':              profile,
        'trainers':             trainers,
        'bookings':             bookings,
        'bmi':                  profile.bmi,
        'bmi_category':         profile.bmi_category,
        'confirmed_count':      bookings.filter(status='confirmed').count(),
        'pending_count':        bookings.filter(status='pending').count(),
        'unread_count':         unread,
        'pending_rate_trainer': pending_rate_trainer,
        'workout_plans':        workout_plans,
        'my_client_ratings':    my_client_ratings,
        'my_site_review':       my_site_review,
    }
    return render(request, 'fitness/lenux.html', context)


@login_required(login_url='/')
@require_POST
def update_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    height = request.POST.get('height', '').strip()
    weight = request.POST.get('weight', '').strip()
    age    = request.POST.get('age', '').strip()
    gender = request.POST.get('gender', '').strip()
    try:
        if height: profile.height_cm = float(height)
        if weight: profile.weight_kg = float(weight)
        if age:    profile.age = int(age)
    except ValueError:
        return JsonResponse({'error': 'Invalid value.'}, status=400)
    if gender:
        profile.gender = gender

    if 'photo' in request.FILES:
        profile.photo = request.FILES['photo']

    profile.save()
    photo_url = profile.photo.url if profile.photo else ''
    return JsonResponse({
        'success': True,
        'bmi': profile.bmi,
        'bmi_category': profile.bmi_category,
        'photo_url': photo_url,
    })


@login_required(login_url='/')
@require_POST
def book_trainer(request):
    trainer_id        = request.POST.get('trainer_id', '').strip()
    notes             = request.POST.get('notes', '').strip()
    total_sessions    = int(request.POST.get('total_sessions', 1))
    session_dates_raw = request.POST.get('session_dates', '[]').strip()

    if not trainer_id:
        return JsonResponse({'error': 'trainer_id required.'}, status=400)
    trainer = get_object_or_404(Trainer, pk=trainer_id)
    existing = BookingRequest.objects.filter(
        member=request.user, trainer=trainer,
        status__in=['pending', 'confirmed']).exists()
    if existing:
        return JsonResponse({'success': False,
                             'message': f'You already have an active booking with {trainer.name}.'})

    total_sessions = max(1, min(total_sessions, 20))
    booking = BookingRequest.objects.create(
        member=request.user, trainer=trainer, notes=notes,
        total_sessions=total_sessions)

    # Save the client-chosen session dates as ScheduledSessions
    try:
        session_dates = json.loads(session_dates_raw)
    except (json.JSONDecodeError, ValueError):
        session_dates = []

    for entry in session_dates[:total_sessions]:
        try:
            date_part = entry.get('date', '')
            time_part = entry.get('time', '08:00')
            if date_part:
                ScheduledSession.objects.create(
                    booking=booking,
                    trainer=trainer,
                    member=request.user,
                    session_date=date_part,
                    session_time=time_part,
                    duration_min=60,
                    location='TBD',
                )
        except Exception:
            pass

    return JsonResponse({'success': True,
                         'message': f'Booking request sent to {trainer.name}!',
                         'booking_id': booking.pk, 'status': booking.status})


@login_required(login_url='/')
@require_POST
def cancel_booking_member(request):
    """Member cancels their own booking."""
    booking_id = request.POST.get('booking_id', '').strip()
    booking = get_object_or_404(BookingRequest, pk=booking_id, member=request.user)
    if booking.status in ('cancelled', 'completed'):
        return JsonResponse({'error': 'Cannot cancel this booking.'}, status=400)
    booking.status = 'cancelled'
    booking.save()
    return JsonResponse({'success': True})


@login_required(login_url='/')
@require_POST
def rate_trainer(request):
    """Member rates a trainer after sessions done or cancellation."""
    booking_id = request.POST.get('booking_id', '').strip()
    stars      = int(request.POST.get('stars', 0))
    comment    = request.POST.get('comment', '').strip()

    if not 1 <= stars <= 5:
        return JsonResponse({'error': 'Stars must be 1-5.'}, status=400)

    booking = get_object_or_404(BookingRequest, pk=booking_id, member=request.user)

    if booking.status not in ('completed', 'cancelled'):
        return JsonResponse({'error': 'Can only rate completed or cancelled sessions.'}, status=400)

    if TrainerRating.objects.filter(booking=booking).exists():
        return JsonResponse({'error': 'Already rated.'}, status=400)

    TrainerRating.objects.create(
        booking=booking, trainer=booking.trainer,
        member=request.user, stars=stars, comment=comment)
    return JsonResponse({'success': True, 'message': 'Thank you for your rating!'})


# ── Messaging ─────────────────────────────────────────────

@login_required(login_url='/')
def chat_view(request, booking_id):
    booking = get_object_or_404(BookingRequest, pk=booking_id)
    trainer = get_trainer_for_user(request.user)
    is_member_of_booking  = (booking.member == request.user)
    is_trainer_of_booking = (trainer and booking.trainer == trainer)

    if not is_member_of_booking and not is_trainer_of_booking and not is_admin(request.user):
        return redirect('home')

    Message.objects.filter(booking=booking, is_read=False).exclude(
        sender=request.user).update(is_read=True)

    messages_qs = booking.messages.select_related('sender').all()
    context = {
        'booking':  booking,
        'messages': messages_qs,
        'trainer':  trainer,
    }
    return render(request, 'fitness/chat.html', context)


@login_required(login_url='/')
@require_POST
def send_message(request, booking_id):
    booking = get_object_or_404(BookingRequest, pk=booking_id)
    trainer = get_trainer_for_user(request.user)

    is_member_of_booking  = (booking.member == request.user)
    is_trainer_of_booking = (trainer and booking.trainer == trainer)
    if not is_member_of_booking and not is_trainer_of_booking:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Empty message.'}, status=400)

    msg = Message.objects.create(booking=booking, sender=request.user, body=body)
    return JsonResponse({
        'success':    True,
        'id':         msg.pk,
        'body':       msg.body,
        'sender':     msg.sender.get_full_name() or msg.sender.username,
        'is_me':      True,
        'sent_at':    msg.sent_at.strftime('%b %d, %H:%M'),
    })


@login_required(login_url='/')
def poll_messages(request, booking_id):
    booking    = get_object_or_404(BookingRequest, pk=booking_id)
    after_id   = int(request.GET.get('after', 0))
    trainer    = get_trainer_for_user(request.user)

    is_member_of_booking  = (booking.member == request.user)
    is_trainer_of_booking = (trainer and booking.trainer == trainer)
    if not is_member_of_booking and not is_trainer_of_booking:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    new_msgs = Message.objects.filter(
        booking=booking, pk__gt=after_id
    ).select_related('sender')

    new_msgs.exclude(sender=request.user).update(is_read=True)

    data = [{
        'id':      m.pk,
        'body':    m.body,
        'sender':  m.sender.get_full_name() or m.sender.username,
        'is_me':   m.sender == request.user,
        'sent_at': m.sent_at.strftime('%b %d, %H:%M'),
    } for m in new_msgs]

    return JsonResponse({'messages': data})


# ── Trainer Dashboard ─────────────────────────────────────

@login_required(login_url='/')
def trainer_dashboard(request):
    if is_admin(request.user):    return redirect('admin_dashboard')
    if not is_trainer(request.user): return redirect('member_dashboard')
    expire_pending_bookings()

    trainer  = get_trainer_for_user(request.user)
    if trainer is None:                      # ← ADD THIS LINE
        return redirect('member_dashboard')  # ← ADD THIS LINE

    bookings = BookingRequest.objects.filter(
        trainer=trainer).select_related('member', 'member__profile').order_by('-requested_at')

    member_ids = bookings.values_list('member_id', flat=True).distinct()
    my_members = User.objects.filter(id__in=member_ids).prefetch_related('profile')

    unread = Message.objects.filter(
        booking__trainer=trainer, is_read=False
    ).exclude(sender=request.user).count()



    # bookings that need client rating from trainer
    pending_rate_client = []
    try:
        for b in bookings:
            if b.status in ('completed', 'cancelled', 'expired'):
                if not ClientRating.objects.filter(booking=b).exists():
                    pending_rate_client.append(b)
    except Exception:
        pending_rate_client = []

    # build a dict of member_id -> avg client rating for display
    member_ratings = {}
    try:
        for uid in member_ids:
           
            try:
                up = UserProfile.objects.get(user_id=uid)
                member_ratings[uid] = {
                'avg': up.avg_rating,
                'count': up.rating_count,
                'ratings': [
            {
                'stars': r['stars'],
                'comment': r['comment'],
                'trainer__name': r['trainer__name'],
                'created_at': r['created_at'].strftime('%b %d, %Y') if r['created_at'] else '',
            }
            for r in ClientRating.objects.filter(
                profile=up
            ).select_related('trainer', 'booking').order_by('-created_at').values(
                'stars', 'comment', 'trainer__name', 'created_at'
            )
        ]
    }
                
                
                
            except Exception:
                member_ratings[uid] = {'avg': None, 'count': 0, 'ratings': []}
    except Exception:
        pass

    context = {
        'trainer':            trainer,
        'bookings':           bookings,
        'members':            my_members,
        'pending_count':      bookings.filter(status='pending').count(),
        'confirmed_count':    bookings.filter(status='confirmed').count(),
        'unread_count':       unread,
        'pending_rate_client': pending_rate_client,
        'member_ratings_json': __import__('json').dumps(member_ratings),
    }
    return render(request, 'fitness/trainer.html', context)


@login_required(login_url='/')
@require_POST
def trainer_update_booking(request):
    if not is_trainer(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    trainer    = get_trainer_for_user(request.user)
    booking_id = request.POST.get('booking_id', '').strip()
    status     = request.POST.get('status', '').strip()
    if status not in ('confirmed', 'cancelled', 'pending', 'completed', 'expired'):
        return JsonResponse({'error': 'Invalid status.'}, status=400)
    booking = get_object_or_404(BookingRequest, pk=booking_id, trainer=trainer)
    booking.status = status
    booking.save()
    return JsonResponse({'success': True, 'status': booking.status})


@login_required(login_url='/')
@require_POST
def trainer_mark_session_done(request):
    """Trainer marks one session as done for a booking."""
    if not is_trainer(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    trainer    = get_trainer_for_user(request.user)
    booking_id = request.POST.get('booking_id', '').strip()
    booking    = get_object_or_404(BookingRequest, pk=booking_id, trainer=trainer)

    if booking.status != 'confirmed':
        return JsonResponse({'error': 'Can only mark sessions for confirmed bookings.'}, status=400)

    if booking.is_sessions_exhausted:
        return JsonResponse({'error': 'All sessions already done.'}, status=400)

    booking.sessions_done += 1
    # If all sessions done, mark as completed
    if booking.sessions_done >= booking.total_sessions:
        booking.status = 'completed'
    booking.save()

    return JsonResponse({
        'success': True,
        'sessions_done': booking.sessions_done,
        'sessions_remaining': booking.sessions_remaining,
        'total_sessions': booking.total_sessions,
        'status': booking.status,
        'completed': booking.status == 'completed',
    })


@login_required(login_url='/')
@require_POST
def trainer_rate_client(request):
    """Trainer rates a client after sessions complete or cancellation."""
    if not is_trainer(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    trainer    = get_trainer_for_user(request.user)
    booking_id = request.POST.get('booking_id', '').strip()
    stars      = int(request.POST.get('stars', 0))
    comment    = request.POST.get('comment', '').strip()

    if not 1 <= stars <= 5:
        return JsonResponse({'error': 'Stars must be 1-5.'}, status=400)

    booking = get_object_or_404(BookingRequest, pk=booking_id, trainer=trainer)

    if booking.status not in ('completed', 'cancelled'):
        return JsonResponse({'error': 'Can only rate completed or cancelled sessions.'}, status=400)

    if ClientRating.objects.filter(booking=booking).exists():
        return JsonResponse({'error': 'Already rated this client for this booking.'}, status=400)

    profile, _ = UserProfile.objects.get_or_create(user=booking.member)
    ClientRating.objects.create(
        booking=booking, profile=profile,
        trainer=trainer, stars=stars, comment=comment)
    return JsonResponse({'success': True, 'message': 'Client rated successfully!'})


@login_required(login_url='/')
@require_POST
def save_workout_plan(request):
    """Trainer creates/updates a workout plan for a client."""
    if not is_trainer(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    trainer    = get_trainer_for_user(request.user)
    booking_id = request.POST.get('booking_id', '').strip()
    title      = request.POST.get('title', '').strip()
    notes      = request.POST.get('notes', '').strip()
    exercises_json = request.POST.get('exercises', '[]')

    if not title:
        return JsonResponse({'error': 'Title is required.'}, status=400)

    booking = get_object_or_404(BookingRequest, pk=booking_id, trainer=trainer)

    try:
        exercises = json.loads(exercises_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid exercises data.'}, status=400)

    plan = WorkoutPlan.objects.create(
        booking=booking, trainer=trainer, member=booking.member,
        title=title, notes=notes)

    for i, ex in enumerate(exercises):
        WorkoutExercise.objects.create(
            plan=plan,
            order=i + 1,
            name=ex.get('name', ''),
            sets=int(ex.get('sets', 3)),
            reps=str(ex.get('reps', '')),
            duration_min=float(ex['duration_min']) if ex.get('duration_min') else None,
        )

    return JsonResponse({'success': True, 'plan_id': plan.pk, 'title': plan.title})


@login_required(login_url='/')
def get_workout_plans_for_booking(request, booking_id):
    """Get workout plans for a specific booking (trainer or member)."""
    booking = get_object_or_404(BookingRequest, pk=booking_id)
    trainer = get_trainer_for_user(request.user)

    is_member = booking.member == request.user
    is_trainer_of = trainer and booking.trainer == trainer

    if not is_member and not is_trainer_of:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    plans = WorkoutPlan.objects.filter(booking=booking).prefetch_related('exercises').order_by('-created_at')
    data = []
    for p in plans:
        data.append({
            'id': p.pk,
            'title': p.title,
            'notes': p.notes,
            'created_at': p.created_at.strftime('%b %d, %Y'),
            'exercises': [{
                'order': ex.order,
                'name': ex.name,
                'sets': ex.sets,
                'reps': ex.reps,
                'duration_min': ex.duration_min,
            } for ex in p.exercises.all()]
        })
    return JsonResponse({'plans': data})


# ── Admin Dashboard ───────────────────────────────────────

@login_required(login_url='/')
def admin_dashboard(request):
    if not is_admin(request.user):
        if is_trainer(request.user): return redirect('trainer_dashboard')
        return redirect('member_dashboard')

    members  = User.objects.filter(
        is_superuser=False, trainer_profile__isnull=True).prefetch_related('profile')
    trainers = Trainer.objects.all()
    bookings = BookingRequest.objects.select_related(
        'member', 'trainer').order_by('-requested_at')

    all_messages = Message.objects.select_related(
        'sender', 'booking__member', 'booking__trainer'
    ).order_by('-sent_at')[:200]

    reported_posts = PostReport.objects.select_related(
        'post', 'post__author', 'reporter'
    ).order_by('is_reviewed', '-created_at')[:100]
    reported_count = PostReport.objects.filter(is_reviewed=False).count()

    context = {
        'total_members':    members.count(),
        'total_trainers':   trainers.count(),
        'total_bookings':   bookings.count(),
        'pending_count':    bookings.filter(status='pending').count(),
        'confirmed_count':  bookings.filter(status='confirmed').count(),
        'cancelled_count':  bookings.filter(status='cancelled').count(),
        'members':  members,
        'trainers': trainers,
        'bookings': bookings,
        'all_messages':    all_messages,
        'reported_posts':  reported_posts,
        'reported_count':  reported_count,
    }
    return render(request, 'fitness/admin.html', context)


@login_required(login_url='/')
@require_POST
def update_booking_status(request):
    if not is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    booking_id = request.POST.get('booking_id', '').strip()
    status     = request.POST.get('status', '').strip()
    if status not in ('confirmed', 'cancelled', 'pending', 'completed', 'expired'):
        return JsonResponse({'error': 'Invalid status.'}, status=400)
    booking = get_object_or_404(BookingRequest, pk=booking_id)
    booking.status = status
    booking.save()
    return JsonResponse({'success': True, 'status': booking.status})


# ── Expire pending bookings ──────────────────────────────
def expire_pending_bookings():
    """Auto-expire pending bookings whose earliest requested session date has passed."""
    try:
        from django.utils import timezone
        from datetime import date, timedelta
        today = date.today()
        pending = BookingRequest.objects.filter(status='pending')
        for b in pending:
            try:
                sessions = b.scheduled_sessions.all()
                if sessions.exists():
                    if all(s.session_date < today for s in sessions):
                        b.status = 'expired'
                        b.save()
                else:
                    if timezone.now() - b.requested_at > timedelta(days=7):
                        b.status = 'expired'
                        b.save()
            except Exception:
                pass
    except Exception:
        pass  # Table may not exist yet — silently skip


@login_required(login_url='/')
def get_booked_slots(request, trainer_id):
    """Return booked date+time slots for a trainer so client picker can block them."""
    trainer = get_object_or_404(Trainer, pk=trainer_id)
    try:
        sessions = ScheduledSession.objects.filter(
            trainer=trainer,
            booking__status__in=['pending', 'confirmed']
        ).values('session_date', 'session_time', 'duration_min')
        data = [{
            'date': str(s['session_date']),
            'time': str(s['session_time'])[:5],
            'duration_min': s['duration_min'],
        } for s in sessions]
    except Exception:
        data = []
    # Also return trainer pricing
    try:
        trainer_rate = float(trainer.hourly_rate) if trainer.hourly_rate else None
    except Exception:
        trainer_rate = None
    return JsonResponse({'booked': data, 'rate': trainer_rate})


@login_required(login_url='/')
def get_unread_count(request):
    """Poll endpoint — returns unread message count for current user."""
    if is_trainer(request.user):
        trainer = get_trainer_for_user(request.user)
        count = Message.objects.filter(
            booking__trainer=trainer, is_read=False
        ).exclude(sender=request.user).count()
    else:
        count = Message.objects.filter(
            booking__member=request.user, is_read=False
        ).exclude(sender=request.user).count()
    return JsonResponse({'unread': count})


# ── Schedule ──────────────────────────────────────────────

@login_required(login_url='/')
@require_POST
def create_scheduled_session(request):
    """Trainer creates a scheduled session for a booking."""
    try:
        if not is_trainer(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        trainer = get_trainer_for_user(request.user)

        booking_id   = request.POST.get('booking_id', '').strip()
        session_date = request.POST.get('session_date', '').strip()
        session_time = request.POST.get('session_time', '').strip()
        duration     = request.POST.get('duration_min', '60').strip()
        location     = request.POST.get('location', 'Gym Floor').strip()
        notes        = request.POST.get('notes', '').strip()

        if not booking_id or not session_date or not session_time:
            return JsonResponse({'error': 'Booking, date and time are required.'}, status=400)

        booking = get_object_or_404(BookingRequest, pk=booking_id, trainer=trainer)

        if booking.status != 'confirmed':
            return JsonResponse({'error': 'Can only schedule sessions for confirmed bookings.'}, status=400)

        try:
            dur = int(duration)
        except (ValueError, TypeError):
            dur = 60

        session = ScheduledSession.objects.create(
            booking=booking,
            trainer=trainer,
            member=booking.member,
            session_date=session_date,
            session_time=session_time,
            duration_min=dur,
            location=location or 'Gym Floor',
            notes=notes,
        )

        # Refresh from DB so date/time are proper Python objects
        session.refresh_from_db()
        return JsonResponse({
            'success': True,
            'id': session.pk,
            'session_date': str(session.session_date),        # YYYY-MM-DD
            'session_time': str(session.session_time)[:5],   # HH:MM
            'duration_min': session.duration_min,
            'location': session.location,
            'notes': session.notes,
            'member_name': booking.member.get_full_name() or booking.member.username,
            'booking_id': booking.pk,
        })
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required(login_url='/')
@require_POST
def delete_scheduled_session(request):
    """Trainer deletes a scheduled session."""
    try:
        if not is_trainer(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        trainer = get_trainer_for_user(request.user)
        session_id = request.POST.get('session_id', '').strip()
        session = get_object_or_404(ScheduledSession, pk=session_id, trainer=trainer)
        session.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required(login_url='/')
def get_trainer_schedule(request):
    """Return all scheduled sessions for the trainer as JSON (for calendar)."""
    try:
        if not is_trainer(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        trainer = get_trainer_for_user(request.user)
        sessions = ScheduledSession.objects.filter(trainer=trainer).select_related('member', 'booking')
        data = [{
            'id': s.pk,
            'booking_id': s.booking.pk,
            'member': s.member.get_full_name() or s.member.username,
            'date': s.session_date.strftime('%Y-%m-%d'),
            'time': s.session_time.strftime('%H:%M'),
            'duration_min': s.duration_min,
            'location': s.location,
            'notes': s.notes,
            'is_done': s.is_done,
        } for s in sessions]
        return JsonResponse({'sessions': data})
    except Exception as e:
        return JsonResponse({'sessions': [], 'error': str(e)})


@login_required(login_url='/')
def get_member_schedule(request):
    """Return all scheduled sessions for the logged-in member."""
    sessions = ScheduledSession.objects.filter(member=request.user).select_related('trainer', 'booking')
    data = [{
        'id': s.pk,
        'booking_id': s.booking.pk,
        'trainer': s.trainer.name,
        'date': s.session_date.strftime('%Y-%m-%d'),
        'time': s.session_time.strftime('%H:%M'),
        'duration_min': s.duration_min,
        'location': s.location,
        'notes': s.notes,
        'booking_status': s.booking.status,
    } for s in sessions]
    return JsonResponse({'sessions': data})


# ── Progress Feed ─────────────────────────────────────────

@login_required(login_url='/')
def feed_list(request):
    """Return all posts as JSON for the progress feed."""
    posts = ProgressPost.objects.select_related('author').prefetch_related(
        'likes', 'comments__author', 'comments__author__profile',
        'images', 'author__profile', 'author__trainer_profile'
    )
    from django.templatetags.static import static as _static
    data = []
    for p in posts:
        author_name = p.author.get_full_name() or p.author.username
        is_trainer_user = hasattr(p.author, 'trainer_profile')
        role = 'Trainer' if is_trainer_user else 'Member'
        # author profile photo
        photo_url = ''
        try:
            prof = p.author.profile
            if prof.photo:
                photo_url = prof.photo.url
        except Exception:
            pass
        if not photo_url and is_trainer_user:
            try:
                key = p.author.trainer_profile.static_photo_key()
                if key:
                    photo_url = _static(key)
            except Exception:
                pass

        # build comments with per-commenter profile photo
        comments = []
        for c in p.comments.all():
            c_photo = ''
            try:
                cp = c.author.profile
                if cp.photo:
                    c_photo = cp.photo.url
            except Exception:
                pass
            if not c_photo:
                try:
                    if hasattr(c.author, 'trainer_profile'):
                        key = c.author.trainer_profile.static_photo_key()
                        if key:
                            c_photo = _static(key)
                except Exception:
                    pass
            c_is_trainer = hasattr(c.author, 'trainer_profile')
            comments.append({
                'id': c.pk,
                'author': c.author.get_full_name() or c.author.username,
                'author_id': c.author_id,
                'photo_url': c_photo,
                'is_trainer': c_is_trainer,
                'body': c.body,
                'created_at': c.created_at.strftime('%b %d, %Y %H:%M'),
            })

        # multiple images: new ProgressPostImage + legacy single image
        image_urls = [img.image.url for img in p.images.all()]
        if not image_urls and p.image:
            image_urls = [p.image.url]

        data.append({
            'id': p.pk,
            'author': author_name,
            'author_id': p.author_id,
            'role': role,
            'is_trainer': is_trainer_user,
            'is_pinned': p.is_pinned,
            'photo_url': photo_url,
            'caption': p.caption,
            'image_url': image_urls[0] if image_urls else '',  # backward compat
            'image_urls': image_urls,
            'created_at': p.created_at.strftime('%b %d, %Y %H:%M'),
            'like_count': p.likes.count(),
            'liked_by_me': request.user in p.likes.all(),
            'comment_count': p.comments.count(),
            'comments': comments,
        })
    return JsonResponse({'posts': data})




@login_required(login_url='/')
def feed_poll(request):
    """
    Lightweight long-poll endpoint for live feed updates.
    Client sends ?since=<epoch_ms> and gets back only new comments + updated like counts.
    """
    try:
        since_ms = int(request.GET.get('since', 0))
    except (ValueError, TypeError):
        since_ms = 0

    from datetime import datetime, timezone as tz
    since_dt = datetime.fromtimestamp(since_ms / 1000.0, tz=tz.utc) if since_ms else None

    from django.templatetags.static import static as _static

    # New comments since timestamp
    qs = PostComment.objects.select_related('author', 'author__profile', 'author__trainer_profile')
    if since_dt:
        qs = qs.filter(created_at__gt=since_dt)
    qs = qs.order_by('created_at')[:100]

    new_comments = []
    for c in qs:
        c_photo = ''
        try:
            if c.author.profile.photo:
                c_photo = c.author.profile.photo.url
        except Exception:
            pass
        if not c_photo:
            try:
                key = c.author.trainer_profile.static_photo_key()
                if key:
                    c_photo = _static(key)
            except Exception:
                pass
        c_is_trainer = hasattr(c.author, 'trainer_profile') and c.author.trainer_profile is not None
        try:
            c_is_trainer = bool(c.author.trainer_profile)
        except Exception:
            c_is_trainer = False

        new_comments.append({
            'id':         c.pk,
            'post_id':    c.post_id,
            'author':     c.author.get_full_name() or c.author.username,
            'author_id':  c.author_id,
            'photo_url':  c_photo,
            'is_trainer': c_is_trainer,
            'body':       c.body,
            'created_at': c.created_at.strftime('%b %d, %Y %H:%M'),
        })

    # Updated like counts for posts that had activity since timestamp
    liked_post_ids = set()
    if since_dt:
        from django.db.models import prefetch_related_objects
        # Get posts whose likes changed — proxy: posts with recent comments
        liked_post_ids = set(
            PostComment.objects.filter(created_at__gt=since_dt)
            .values_list('post_id', flat=True)
        )

    like_updates = []
    for pid in liked_post_ids:
        try:
            post = ProgressPost.objects.get(pk=pid)
            like_updates.append({
                'post_id':    pid,
                'like_count': post.likes.count(),
                'comment_count': post.comments.count(),
            })
        except ProgressPost.DoesNotExist:
            pass

    # Server time so client can use it as next `since`
    from django.utils import timezone
    now_ms = int(timezone.now().timestamp() * 1000)

    return JsonResponse({
        'ok':           True,
        'server_time':  now_ms,
        'new_comments': new_comments,
        'like_updates': like_updates,
    })

@login_required(login_url='/')
@require_POST
def feed_create_post(request):
    caption = request.POST.get('caption', '').strip()
    images  = request.FILES.getlist('images')  # multiple images
    # Also accept legacy single 'image' key
    if not images and request.FILES.get('image'):
        images = [request.FILES.get('image')]
    if not caption and not images:
        return JsonResponse({'error': 'Caption or image is required.'}, status=400)
    post = ProgressPost.objects.create(author=request.user, caption=caption)
    for i, img in enumerate(images):
        ProgressPostImage.objects.create(post=post, image=img, order=i)
    return JsonResponse({'ok': True, 'post_id': post.pk})


@login_required(login_url='/')
@require_POST
def feed_toggle_like(request):
    data    = json.loads(request.body)
    post_id = data.get('post_id')
    post    = get_object_or_404(ProgressPost, pk=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    return JsonResponse({'ok': True, 'liked': liked, 'like_count': post.likes.count()})


@login_required(login_url='/')
@require_POST
def feed_add_comment(request):
    data    = json.loads(request.body)
    post_id = data.get('post_id')
    body    = data.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Comment cannot be empty.'}, status=400)
    post    = get_object_or_404(ProgressPost, pk=post_id)
    comment = PostComment.objects.create(post=post, author=request.user, body=body)
    return JsonResponse({
        'ok': True,
        'comment': {
            'id': comment.pk,
            'author': request.user.get_full_name() or request.user.username,
            'author_id': request.user.pk,
            'body': comment.body,
            'created_at': comment.created_at.strftime('%b %d, %Y %H:%M'),
        }
    })


@login_required(login_url='/')
@require_POST
def feed_report_post(request):
    """Member reports a progress post for admin moderation."""
    try:
        data      = json.loads(request.body)
        post_id   = data.get('post_id')
        reason    = data.get('reason', 'other')
        detail    = data.get('detail', '').strip()
        post      = get_object_or_404(ProgressPost, pk=post_id)
        if post.author == request.user:
            return JsonResponse({'error': 'You cannot report your own post.'}, status=400)
        obj, created = PostReport.objects.get_or_create(
            post=post, reporter=request.user,
            defaults={'reason': reason, 'detail': detail}
        )
        if not created:
            return JsonResponse({'error': 'You have already reported this post.'}, status=400)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/')
@require_POST
def feed_delete_post(request):
    data    = json.loads(request.body)
    post_id = data.get('post_id')
    post    = get_object_or_404(ProgressPost, pk=post_id)
    if post.author != request.user and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied.'}, status=403)
    post.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/')
@require_POST
def feed_delete_comment(request):
    data       = json.loads(request.body)
    comment_id = data.get('comment_id')
    comment    = get_object_or_404(PostComment, pk=comment_id)
    if comment.author != request.user and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied.'}, status=403)
    comment.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/')
@require_POST
def admin_dismiss_report(request):
    """Admin marks a report as reviewed (no action) or deletes the post."""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        data      = json.loads(request.body)
        report_id = data.get('report_id')
        action    = data.get('action', 'dismiss')  # 'dismiss' or 'delete'
        report    = get_object_or_404(PostReport, pk=report_id)
        if action == 'delete':
            report.post.delete()
        else:
            report.is_reviewed = True
            report.save()
            # Mark all reports on same post as reviewed
            PostReport.objects.filter(post=report.post).update(is_reviewed=True)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── Site Reviews ─────────────────────────────────────────

@login_required(login_url='/')
@require_POST
def submit_site_review(request):
    """Client submits a review/rating about the website."""
    stars   = int(request.POST.get('stars', 0))
    comment = request.POST.get('comment', '').strip()
    if not 1 <= stars <= 5:
        return JsonResponse({'error': 'Stars must be 1-5.'}, status=400)
    try:
        review = SiteReview.objects.get(user=request.user)
        review.stars = stars
        review.comment = comment
        review.is_approved = True
        review.save()
        created = False
    except SiteReview.DoesNotExist:
        SiteReview.objects.create(user=request.user, stars=stars, comment=comment)
        created = True
    return JsonResponse({'success': True, 'created': created})


# ── Feed: pin post (admin only) ───────────────────────────

@login_required(login_url='/')
@require_POST
def feed_pin_post(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    data    = json.loads(request.body)
    post_id = data.get('post_id')
    post    = get_object_or_404(ProgressPost, pk=post_id)
    post.is_pinned = not post.is_pinned
    post.save()
    return JsonResponse({'ok': True, 'pinned': post.is_pinned})


# ═══════════════════════════════════════════════════════════
# ANALYTICS VIEWS
# ═══════════════════════════════════════════════════════════

import json as _json


# ── Analytics pages (template views) ────────────────────

@login_required(login_url='/')
def analytics_page(request):
    """Serve the analytics template with the correct role."""
    if is_admin(request.user):
        role = 'admin'
    elif is_trainer(request.user):
        role = 'trainer'
    else:
        role = 'client'
    return render(request, 'fitness/analytics.html', {'role': role})


# ── Client Analytics ──────────────────────────────────────

@login_required(login_url='/')
def client_analytics(request):
    """Return analytics data for the logged-in member as JSON."""
    user = request.user
    today = date.today()
    year  = today.year

    # ── Booking / session stats ──────────────────────────
    all_bookings = BookingRequest.objects.filter(member=user)
    total_sessions_booked  = all_bookings.aggregate(s=Sum('total_sessions'))['s'] or 0
    total_sessions_done    = all_bookings.aggregate(s=Sum('sessions_done'))['s'] or 0
    completion_rate = round((total_sessions_done / total_sessions_booked * 100) if total_sessions_booked else 0, 1)

    # Sessions per month (last 6 months)
    monthly_sessions = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        m = m_date.month
        y = m_date.year
        count = ScheduledSession.objects.filter(
            member=user,
            session_date__year=y,
            session_date__month=m,
            is_done=True
        ).count()
        monthly_sessions.append({
            'month': m_date.strftime('%b %Y'),
            'sessions': count,
        })

    # Most active day of week
    scheduled = ScheduledSession.objects.filter(member=user, is_done=True)
    day_counts = [0] * 7
    for s in scheduled:
        day_counts[s.session_date.weekday()] += 1
    days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    most_active_day = days[day_counts.index(max(day_counts))] if any(day_counts) else None
    weekly_attendance = [{'day': days[i], 'sessions': day_counts[i]} for i in range(7)]

    # ── Weight / BMI progress ────────────────────────────
    weight_logs = list(WeightLog.objects.filter(member=user).order_by('logged_at')
                       .values('weight_kg', 'logged_at', 'note'))
    weight_change = None
    if len(weight_logs) >= 2:
        weight_change = round(weight_logs[-1]['weight_kg'] - weight_logs[0]['weight_kg'], 1)

    profile = getattr(user, 'profile', None)
    current_bmi = profile.bmi if profile else None

    # ── Goals ────────────────────────────────────────────
    goals = list(FitnessGoal.objects.filter(member=user)
                 .values('id','goal_type','target_weight','target_date','is_active','is_achieved','created_at'))
    for g in goals:
        if g['target_date']:
            g['target_date'] = str(g['target_date'])
        g['created_at'] = str(g['created_at'])[:10]

    # ── Trainer ratings given ────────────────────────────
    ratings_given = TrainerRating.objects.filter(member=user).select_related('trainer')
    trainer_ratings = [{'trainer': r.trainer.name, 'stars': r.stars, 'comment': r.comment} for r in ratings_given]

    # ── Trainer info ─────────────────────────────────────
    confirmed_bookings = all_bookings.filter(status__in=['confirmed','completed'])
    trainers_used = list(confirmed_bookings.values_list('trainer__name', flat=True).distinct())

    # ── Upcoming sessions ────────────────────────────────
    upcoming = ScheduledSession.objects.filter(
        member=user, session_date__gte=today, is_done=False
    ).select_related('trainer').order_by('session_date', 'session_time')[:5]
    upcoming_data = [{'date': str(s.session_date), 'time': str(s.session_time)[:5],
                      'trainer': s.trainer.name, 'location': s.location} for s in upcoming]

    return JsonResponse({
        'total_sessions_booked':  total_sessions_booked,
        'total_sessions_done':    total_sessions_done,
        'completion_rate':        completion_rate,
        'monthly_sessions':       monthly_sessions,
        'weekly_attendance':      weekly_attendance,
        'most_active_day':        most_active_day,
        'weight_logs':            [{'date': str(w['logged_at']), 'weight': w['weight_kg'], 'note': w['note']} for w in weight_logs],
        'weight_change':          weight_change,
        'current_bmi':            current_bmi,
        'bmi_category':           profile.bmi_category if profile else None,
        'goals':                  goals,
        'trainer_ratings':        trainer_ratings,
        'trainers_used':          trainers_used,
        'upcoming_sessions':      upcoming_data,
        'bookings_by_status': {
            'pending':   all_bookings.filter(status='pending').count(),
            'confirmed': all_bookings.filter(status='confirmed').count(),
            'completed': all_bookings.filter(status='completed').count(),
            'cancelled': all_bookings.filter(status='cancelled').count(),
            'expired':   all_bookings.filter(status='expired').count(),
        },
    })


@login_required(login_url='/')
@require_POST
def log_weight(request):
    """Member logs their current weight."""
    try:
        weight = float(request.POST.get('weight_kg', 0))
        note   = request.POST.get('note', '').strip()
        if not weight or weight <= 0:
            return JsonResponse({'error': 'Invalid weight.'}, status=400)
        log = WeightLog.objects.create(member=request.user, weight_kg=weight, note=note)
        # Also update profile weight
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.weight_kg = weight
        profile.save()
        return JsonResponse({'success': True, 'date': str(log.logged_at), 'weight': weight})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/')
@require_POST
def save_goal(request):
    """Member sets or updates a fitness goal."""
    try:
        goal_type     = request.POST.get('goal_type', '').strip()
        target_weight = request.POST.get('target_weight', '').strip()
        target_date   = request.POST.get('target_date', '').strip()

        if not goal_type:
            return JsonResponse({'error': 'Goal type required.'}, status=400)

        # Deactivate previous goals of same type
        FitnessGoal.objects.filter(member=request.user, goal_type=goal_type, is_active=True).update(is_active=False)

        goal = FitnessGoal.objects.create(
            member=request.user,
            goal_type=goal_type,
            target_weight=float(target_weight) if target_weight else None,
            target_date=target_date if target_date else None,
        )
        return JsonResponse({'success': True, 'goal_id': goal.pk, 'goal_type': goal.get_goal_type_display()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/')
@require_POST
def achieve_goal(request):
    """Mark a goal as achieved."""
    try:
        goal_id = request.POST.get('goal_id')
        goal = get_object_or_404(FitnessGoal, pk=goal_id, member=request.user)
        goal.is_achieved = True
        goal.is_active = False
        goal.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── Trainer Analytics ─────────────────────────────────────

@login_required(login_url='/')
def trainer_analytics(request):
    """Return analytics data for the logged-in trainer as JSON."""
    if not is_trainer(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    trainer = get_trainer_for_user(request.user)
    today   = date.today()

    bookings = BookingRequest.objects.filter(trainer=trainer)
    member_ids = bookings.values_list('member_id', flat=True).distinct()
    total_clients = member_ids.count()

    # Sessions per month (last 6 months)
    monthly_sessions = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        m, y = m_date.month, m_date.year
        count = ScheduledSession.objects.filter(
            trainer=trainer, session_date__year=y, session_date__month=m
        ).count()
        done  = ScheduledSession.objects.filter(
            trainer=trainer, session_date__year=y, session_date__month=m, is_done=True
        ).count()
        monthly_sessions.append({'month': m_date.strftime('%b %Y'), 'total': count, 'done': done})

    # Total sessions handled
    total_scheduled = ScheduledSession.objects.filter(trainer=trainer).count()
    total_done      = ScheduledSession.objects.filter(trainer=trainer, is_done=True).count()
    completion_rate = round((total_done / total_scheduled * 100) if total_scheduled else 0, 1)

    # Client attendance: sessions_done / total_sessions per confirmed booking
    client_data = []
    for b in bookings.filter(status__in=['confirmed','completed']).select_related('member'):
        sessions_scheduled = ScheduledSession.objects.filter(booking=b).count()
        sessions_done      = ScheduledSession.objects.filter(booking=b, is_done=True).count()
        att_rate = round((sessions_done / sessions_scheduled * 100) if sessions_scheduled else 0)
        client_data.append({
            'name':        b.member.get_full_name() or b.member.username,
            'sessions':    b.total_sessions,
            'done':        b.sessions_done,
            'attendance':  att_rate,
            'status':      b.status,
            'booking_id':  b.pk,
        })

    # Inactive clients: confirmed bookings with no sessions in last 14 days
    two_weeks_ago = today - timedelta(days=14)
    inactive = []
    for b in bookings.filter(status='confirmed').select_related('member'):
        recent = ScheduledSession.objects.filter(
            booking=b, session_date__gte=two_weeks_ago
        ).exists()
        if not recent:
            inactive.append(b.member.get_full_name() or b.member.username)

    # Ratings received
    avg_rating  = trainer.avg_rating
    rating_count = trainer.rating_count
    rating_breakdown = {}
    for i in range(1, 6):
        rating_breakdown[str(i)] = TrainerRating.objects.filter(trainer=trainer, stars=i).count()

    # Upcoming sessions
    upcoming = ScheduledSession.objects.filter(
        trainer=trainer, session_date__gte=today, is_done=False
    ).select_related('member').order_by('session_date', 'session_time')[:8]
    upcoming_data = [{'date': str(s.session_date), 'time': str(s.session_time)[:5],
                      'member': s.member.get_full_name() or s.member.username,
                      'location': s.location} for s in upcoming]

    # Workout plans created
    plans_count = WorkoutPlan.objects.filter(trainer=trainer).count()

    # Booking status breakdown
    status_breakdown = {
        'pending':   bookings.filter(status='pending').count(),
        'confirmed': bookings.filter(status='confirmed').count(),
        'completed': bookings.filter(status='completed').count(),
        'cancelled': bookings.filter(status='cancelled').count(),
    }

    return JsonResponse({
        'total_clients':     total_clients,
        'total_scheduled':   total_scheduled,
        'total_done':        total_done,
        'completion_rate':   completion_rate,
        'monthly_sessions':  monthly_sessions,
        'client_data':       client_data,
        'inactive_clients':  inactive,
        'avg_rating':        avg_rating,
        'rating_count':      rating_count,
        'rating_breakdown':  rating_breakdown,
        'upcoming_sessions': upcoming_data,
        'plans_count':       plans_count,
        'status_breakdown':  status_breakdown,
    })


# ── Admin Analytics ───────────────────────────────────────

@login_required(login_url='/')
def admin_analytics(request):
    """Return site-wide analytics for admin."""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    today = date.today()

    # Members
    all_members = User.objects.filter(is_superuser=False, trainer_profile__isnull=True)
    total_members  = all_members.count()
    new_this_month = all_members.filter(
        date_joined__year=today.year, date_joined__month=today.month).count()
    new_this_week  = all_members.filter(date_joined__gte=today - timedelta(days=7)).count()

    # Registrations per month (last 6)
    reg_trend = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        m, y = m_date.month, m_date.year
        count = all_members.filter(date_joined__year=y, date_joined__month=m).count()
        reg_trend.append({'month': m_date.strftime('%b %Y'), 'members': count})

    # Trainers
    total_trainers    = Trainer.objects.count()
    available_trainers = Trainer.objects.filter(is_available=True).count()

    # Bookings
    all_bookings = BookingRequest.objects.all()
    booking_stats = {
        'total':     all_bookings.count(),
        'pending':   all_bookings.filter(status='pending').count(),
        'confirmed': all_bookings.filter(status='confirmed').count(),
        'completed': all_bookings.filter(status='completed').count(),
        'cancelled': all_bookings.filter(status='cancelled').count(),
        'expired':   all_bookings.filter(status='expired').count(),
    }

    # Bookings per month (last 6)
    booking_trend = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        m, y = m_date.month, m_date.year
        count    = all_bookings.filter(requested_at__year=y, requested_at__month=m).count()
        done     = all_bookings.filter(requested_at__year=y, requested_at__month=m, status='completed').count()
        booking_trend.append({'month': m_date.strftime('%b %Y'), 'bookings': count, 'completed': done})

    # Sessions
    all_sessions = ScheduledSession.objects.all()
    total_sessions_done = all_sessions.filter(is_done=True).count()
    total_sessions_all  = all_sessions.count()

    # Most popular specialty
    specialty_counts = {}
    for t in Trainer.objects.all():
        label = t.get_specialty_display()
        booked = BookingRequest.objects.filter(trainer=t).count()
        specialty_counts[label] = specialty_counts.get(label, 0) + booked

    specialty_data = [{'specialty': k, 'bookings': v} for k, v in
                      sorted(specialty_counts.items(), key=lambda x: -x[1])]

    # Trainer leaderboard by rating
    trainer_leaderboard = []
    for t in Trainer.objects.all():
        trainer_leaderboard.append({
            'name':         t.name,
            'specialty':    t.get_specialty_display(),
            'avg_rating':   t.avg_rating or 0,
            'rating_count': t.rating_count,
            'bookings':     BookingRequest.objects.filter(trainer=t).count(),
            'sessions_done': ScheduledSession.objects.filter(trainer=t, is_done=True).count(),
        })
    trainer_leaderboard.sort(key=lambda x: (-x['avg_rating'], -x['bookings']))

    # Gender distribution of members
    gender_dist = {}
    for g, label in [('male','Male'),('female','Female'),('other','Other')]:
        count = UserProfile.objects.filter(gender=g).count()
        if count:
            gender_dist[label] = count

    # Age distribution
    age_groups = {'Under 20': 0, '20-29': 0, '30-39': 0, '40-49': 0, '50+': 0}
    for p in UserProfile.objects.exclude(age=None):
        a = p.age
        if a < 20:    age_groups['Under 20'] += 1
        elif a < 30:  age_groups['20-29'] += 1
        elif a < 40:  age_groups['30-39'] += 1
        elif a < 50:  age_groups['40-49'] += 1
        else:         age_groups['50+'] += 1
    age_data = [{'group': k, 'count': v} for k, v in age_groups.items() if v]

    # Messages
    total_messages = Message.objects.count()
    messages_today = Message.objects.filter(sent_at__date=today).count()

    # Site reviews
    avg_site_rating = SiteReview.objects.aggregate(avg=Avg('stars'))['avg']

    # Peak booking days
    from django.db.models.functions import ExtractWeekDay
    day_names = ['', 'Sun','Mon','Tue','Wed','Thu','Fri','Sat']
    peak_days_qs = (all_bookings
        .annotate(wd=ExtractWeekDay('requested_at'))
        .values('wd').annotate(count=Count('id'))
        .order_by('wd'))
    peak_days = [{'day': day_names[p['wd']], 'bookings': p['count']} for p in peak_days_qs]

    return JsonResponse({
        'total_members':       total_members,
        'new_this_month':      new_this_month,
        'new_this_week':       new_this_week,
        'reg_trend':           reg_trend,
        'total_trainers':      total_trainers,
        'available_trainers':  available_trainers,
        'booking_stats':       booking_stats,
        'booking_trend':       booking_trend,
        'total_sessions_done': total_sessions_done,
        'total_sessions_all':  total_sessions_all,
        'specialty_data':      specialty_data,
        'trainer_leaderboard': trainer_leaderboard,
        'gender_dist':         [{'gender': k, 'count': v} for k, v in gender_dist.items()],
        'age_data':            age_data,
        'total_messages':      total_messages,
        'messages_today':      messages_today,
        'avg_site_rating':     round(avg_site_rating, 1) if avg_site_rating else None,
        'peak_days':           peak_days,
    })
