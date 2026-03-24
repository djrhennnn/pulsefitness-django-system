from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/',    views.user_login, name='login'),
    path('logout/',   views.user_logout, name='logout'),

    # Member
    path('dashboard/',                        views.member_dashboard,      name='member_dashboard'),
    path('dashboard/update-profile/',         views.update_profile,        name='update_profile'),
    path('dashboard/book-trainer/',           views.book_trainer,          name='book_trainer'),
    path('dashboard/cancel-booking/',         views.cancel_booking_member, name='cancel_booking_member'),
    path('dashboard/rate-trainer/',           views.rate_trainer,          name='rate_trainer'),
    path('dashboard/my-schedule/',            views.get_member_schedule,   name='member_schedule'),
    path('dashboard/booked-slots/<int:trainer_id>/', views.get_booked_slots, name='booked_slots'),

    # Chat
    path('chat/<int:booking_id>/',            views.chat_view,    name='chat'),
    path('chat/<int:booking_id>/send/',       views.send_message, name='send_message'),
    path('chat/<int:booking_id>/poll/',       views.poll_messages, name='poll_messages'),

    # Trainer
    path('trainer/',                          views.trainer_dashboard,         name='trainer_dashboard'),
    path('trainer/booking/update/',           views.trainer_update_booking,    name='trainer_update_booking'),
    path('trainer/booking/session-done/',     views.trainer_mark_session_done, name='trainer_mark_session_done'),
    path('trainer/rate-client/',              views.trainer_rate_client,       name='trainer_rate_client'),
    path('trainer/save-workout-plan/',        views.save_workout_plan,         name='save_workout_plan'),
    path('trainer/workout-plans/<int:booking_id>/', views.get_workout_plans_for_booking, name='get_workout_plans'),
    path('trainer/schedule/create/',          views.create_scheduled_session,  name='create_scheduled_session'),
    path('trainer/schedule/delete/',          views.delete_scheduled_session,  name='delete_scheduled_session'),
    path('trainer/schedule/list/',            views.get_trainer_schedule,      name='get_trainer_schedule'),

    # Admin
    path('admin-panel/',                      views.admin_dashboard,       name='admin_dashboard'),
    path('admin-panel/booking/update/',       views.update_booking_status, name='update_booking_status'),
]
