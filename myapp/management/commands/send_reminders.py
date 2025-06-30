from django.core.management.base import BaseCommand
from django.utils import timezone
from ...models import Notification, UserProfile  
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.db import models

User = get_user_model()

class Command(BaseCommand):
    help = 'Sends daily learning reminders'
    
    def handle(self, *args, **options):
        today = timezone.now().date()

        # ✅ Remove broken `available_days` filter
        users_to_notify = User.objects.filter(
            userprofile__last_activity_date__lt=today,
            userprofile__daily_goal_completed__lt=models.F('userprofile__daily_goal')
        )

        for user in users_to_notify:
            Notification.objects.create(
                user=user,
                title="Daily Reminder",
                message="Don't forget to complete your daily goal to keep your streak alive!",
                notification_type="reminder"
            )

        self.stdout.write(f"✅ Sent reminders to {users_to_notify.count()} users")
