# send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from models import Notification
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Sends daily learning reminders'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        users_to_notify = User.objects.filter(
            profile__last_activity_date__lt=today
        ).select_related('profile')
        
        for user in users_to_notify:
            Notification.objects.create(
                user=user,
                title="Daily Learning Reminder",
                message="Don't forget to complete your daily lesson to maintain your streak!",
                notification_type="reminder"
            )
        
        self.stdout.write(f"Sent reminders to {users_to_notify.count()} users")