from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from myapp.models import UserProfile, Notification
from django.utils.timezone import localtime
import logging

logger = logging.getLogger(__name__)

def send_daily_reminder_emails():
    now = localtime()  # Uses your TIME_ZONE from settings.py
    current_time = now.time().replace(second=0, microsecond=0)

    # Safe 2-minute window (1 minute before, 1 minute after)
    window_start = (now - timedelta(minutes=1)).time()
    window_end = (now + timedelta(minutes=1)).time()

    print(f"🔍 Local time: {current_time}")
    print(f"⏰ Time window: {window_start} → {window_end}")

    profiles = UserProfile.objects.filter(
        daily_reminder=True,
        reminder_time__gte=window_start,
        reminder_time__lte=window_end
    ).select_related('user')

    print(f"📬 Found {profiles.count()} users to notify")

    for profile in profiles:
        user = profile.user
        if not user.email:
            continue

        try:
            # Send email
            send_mail(
                subject="⏰ Don't forget your daily practice!",
                message=f"Hi {user.username}, just a reminder to complete your daily goal on Speakably!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            # Create notification
            Notification.objects.create(
                user=user,
                title="Daily Reminder",
                message="Don't forget to complete your daily goal!",
                notification_type="reminder"
            )

            print(f"✅ Sent reminder to {user.email}")
            logger.info(f"✅ Reminder email sent to {user.email}")

        except Exception as e:
            print(f"❌ Failed to send reminder to {user.email}: {str(e)}")
            logger.error(f"❌ Failed to send reminder to {user.email}: {str(e)}")
