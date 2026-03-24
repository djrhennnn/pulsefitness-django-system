from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, Trainer, BookingRequest, Message


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'age', 'gender', 'height_cm', 'weight_kg', 'bmi_display', 'photo_thumb')
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_filter   = ('gender',)
    readonly_fields = ('photo_thumb',)

    def bmi_display(self, obj):
        b = obj.bmi
        if b is None:
            return '—'
        color = '#93c5fd' if b < 18.5 else '#86efac' if b < 25 else '#fde047' if b < 30 else '#fca5a5'
        return format_html('<span style="color:{};font-weight:700">{}</span>', color, b)
    bmi_display.short_description = 'BMI'

    def photo_thumb(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:50%;border:2px solid #00f3ff">', obj.photo.url)
        return '—'
    photo_thumb.short_description = 'Photo'


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display   = ('photo_thumb', 'name', 'specialty', 'is_available', 'availability_badge', 'booking_count', 'user')
    list_filter    = ('specialty', 'is_available')
    search_fields  = ('name', 'bio')
    list_editable  = ('is_available',)
    readonly_fields = ('photo_preview', 'booking_count')
    fields = ('user', 'name', 'nickname', 'specialty', 'bio', 'is_available', 'photo', 'photo_preview')

    def photo_thumb(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width:44px;height:44px;object-fit:cover;object-position:top;border-radius:50%;border:2px solid #00f3ff">', obj.photo.url)
        return format_html('<div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#00f3ff,#b026ff);display:flex;align-items:center;justify-content:center;font-weight:800;color:#000">{}</div>', obj.name[0].upper())
    photo_thumb.short_description = ''

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-width:200px;max-height:200px;border-radius:12px;object-fit:cover;object-position:top">', obj.photo.url)
        return 'No photo uploaded'
    photo_preview.short_description = 'Current Photo'

    def availability_badge(self, obj):
        if obj.is_available:
            return format_html('<span style="background:rgba(34,197,94,.2);color:#22c55e;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid rgba(34,197,94,.4)">Available</span>')
        return format_html('<span style="background:rgba(239,68,68,.2);color:#f87171;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid rgba(239,68,68,.4)">Booked Out</span>')
    availability_badge.short_description = 'Status'

    def booking_count(self, obj):
        return obj.bookings.count()
    booking_count.short_description = 'Bookings'


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display   = ('member', 'trainer', 'status_badge', 'requested_at', 'msg_count')
    list_filter    = ('status', 'trainer')
    search_fields  = ('member__username', 'member__email', 'trainer__name')
    list_editable  = ()
    readonly_fields = ('requested_at', 'msg_count')
    ordering       = ('-requested_at',)

    def status_badge(self, obj):
        colors = {
            'pending':   ('rgba(251,191,36,.2)', '#fbbf24', 'rgba(251,191,36,.4)'),
            'confirmed': ('rgba(34,197,94,.2)',  '#22c55e', 'rgba(34,197,94,.4)'),
            'cancelled': ('rgba(239,68,68,.2)',  '#f87171', 'rgba(239,68,68,.4)'),
        }
        bg, tc, border = colors.get(obj.status, ('#333','#fff','#555'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid {}">{}</span>',
            bg, tc, border, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def msg_count(self, obj):
        c = obj.messages.count()
        return format_html('<span style="color:#00f3ff;font-weight:700">{}</span>', c) if c else '0'
    msg_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ('sender', 'booking_link', 'short_body', 'sent_at', 'is_read')
    list_filter   = ('is_read',)
    search_fields = ('sender__username', 'body')
    readonly_fields = ('sent_at',)
    ordering      = ('-sent_at',)

    def booking_link(self, obj):
        return format_html('{} → {}', obj.booking.member.username, obj.booking.trainer.name)
    booking_link.short_description = 'Conversation'

    def short_body(self, obj):
        return obj.body[:60] + '…' if len(obj.body) > 60 else obj.body
    short_body.short_description = 'Message'


# ── Admin site branding ──────────────────────────────────
admin.site.site_header  = '⚡ PulseFitness Admin'
admin.site.site_title   = 'PulseFitness'
admin.site.index_title  = 'Management Dashboard'
