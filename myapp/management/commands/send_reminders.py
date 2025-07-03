from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging

from myapp.management.commands.reminders import send_daily_reminder_emails


from myapp.management.commands.reminders import send_daily_reminder_emails
from ...models import User, Notification

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders to users at their preferred time.'

    def handle(self, *args, **kwargs):
        count = send_daily_reminder_emails()
        self.stdout.write(f"✅ Sent reminders to {count} users.")

        
        start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        end = start + timedelta(days=1)

        users_to_notify = User.objects.filter(
    userprofile__last_activity_date__gte=start,
    userprofile__last_activity_date__lt=end,
    userprofile__daily_goal_completed__lt=F('userprofile__daily_goal'),
    email__isnull=False,
    email__gt=''
).select_related('userprofile')

        count = 0
        for user in users_to_notify:
            try:
                send_mail(
                    "Don't forget your daily language practice!",
                    f"Hi {user.username},\n\nYou're doing great with your language learning! "
                    f"Don't forget to complete your daily goal today to keep your streak going.\n\n"
                    f"The Speakabily Team",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )

                Notification.objects.create(
                    user=user,
                    title="Daily Reminder",
                    message="Don't forget to complete your daily goal!",
                    notification_type="reminder"
                )

                count += 1
                logger.info(f"Sent reminder to {user.email}")

            except Exception as e:
                logger.error(f"Failed to send reminder to {user.email}: {str(e)}")

        self.stdout.write(f"✅ Sent reminders to {count} users")

        
