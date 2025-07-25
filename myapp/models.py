from django.db import models
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token as AuthToken
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q

class Language(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)  # e.g., "fr", "es"
    flag = models.CharField(max_length=10, default='🌐')
    speech_recognition_code = models.CharField(
        max_length=10,
        default='en-US',
        help_text='Language code for speech recognition (e.g., fr-FR for French)'
    )
    
    def clean(self):
        # Validate the speech recognition code format
        if not (len(self.speech_recognition_code) == 5 and 
                self.speech_recognition_code[2] == '-'):
            raise ValidationError(
                'Speech recognition code must be in format like "fr-FR"'
            )

    class Meta:
        indexes = [
            models.Index(fields=['code']),
        ]
        
    def __str__(self):
        return self.name

class Unit(models.Model):
    proficiency = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'), 
            ('advanced', 'Advanced')
        ],
        default='beginner'
    )
    language = models.ForeignKey(
        'Language', 
        on_delete=models.CASCADE,
        related_name='units'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Unit Title',
        help_text='Enter a title for this unit'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Sort Order',
        help_text='Determines display order (lower numbers first)'
    )
    icon = models.CharField(
        max_length=50, 
        default='📚',
        verbose_name='Display Icon',
        help_text='Icon to represent this unit'
    )

    @property
    def is_completed(self, user=None):
        if not user or not user.is_authenticated:
            return False
            
        # Check if all lessons in this unit are completed
        lessons = self.lessons.all()
        if not lessons.exists():
            return False
            
        return all(
            lesson.get_is_completed(user) 
            for lesson in lessons
        )
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Learning Unit'
        verbose_name_plural = 'Learning Units'
        constraints = [
            models.UniqueConstraint(
                fields=['language', 'title'],
                name='unique_unit_title_per_language'
            )
        ]
        indexes = [
            models.Index(fields=['language']),
        ]
        
    def __str__(self):
        return f"{self.language.name} - {self.title}"

# In models.py - Clean up the Lesson model to remove exercise-related fields
class Lesson(models.Model):
    is_unlocked = models.BooleanField(default=True)
    prerequisite = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unlocks'
    )

    
    def get_is_completed(self, user):
        if not user or not user.is_authenticated:
            return False
        return LessonProgress.objects.filter(
            lesson=self,
            user=user,
            is_completed=True
        ).exists()
    def set_request(self, request):
        self._request = request
    
    def save(self, *args, **kwargs):
        # Auto-set is_unlocked based on prerequisites
        if self.prerequisite:
            self.is_unlocked = self.prerequisite.is_completed_for_user(self.created_by)
        super().save(*args, **kwargs)
    
    def is_completed_for_user(self, user):
        return self.user_progress.filter(user=user, is_completed=True).exists()
    LESSON_TYPES = [
        ('vocabulary', 'Vocabulary'),
        ('grammar', 'Grammar'),
        ('listening', 'Listening'),
        ('speaking', 'Speaking'),
        ('practice', 'Practice'),
    ]
    
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='lessons',
        null=True,  # Important for nested creation
        blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content = models.TextField(blank=True, null=True)
    xp_reward = models.PositiveIntegerField(default=10) 

    class Meta:
        ordering = ['order']
        
        

    def __str__(self):
        return f"{self.unit.title} - {self.title}"
    

class UserLanguage(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    proficiency = models.CharField(max_length=20, default='beginner')

    def __str__(self):
      username = self.user.user.username if self.user and self.user.user else "Unknown"
      language = self.language.name if self.language else "No Language"
      return f"{username} - {language}"


    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    selected_language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        related_name='selected_by_users'  # ✅ resolves reverse accessor conflict
    )

    proficiency_level = models.CharField(max_length=50, default='beginner')
    daily_goal = models.PositiveIntegerField(default=5)
    daily_goal_completed = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(default=timezone.now)
    last_streak_date = models.DateField(null=True, blank=True)
    xp = models.PositiveIntegerField(default=0)
    hearts = models.PositiveIntegerField(default=5)
    gems = models.PositiveIntegerField(default=0)
    reminders_enabled = models.BooleanField(default=False)
    daily_push = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)  # preferred time of day
    reminders_enabled = models.BooleanField(default=False)
    
    daily_reminder = models.BooleanField(default=True)
    weekly_summary = models.BooleanField(default=True)


    learning_languages = models.ManyToManyField(
        Language,
        through='UserLanguage',
        related_name='learned_by_users'  # ✅ avoids reverse clash
    )

    def __str__(self):
        return self.user.username

    
    

    def get_completed_lessons(self):
        return Lesson.objects.filter(
            user_progress__user=self.user,
            user_progress__is_completed=True
        )
    
    def update_streak(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        if self.last_activity_date == yesterday:
            self.current_streak += 1
        elif self.last_activity_date != today:
            self.current_streak = 1
        
        self.last_activity_date = today
        self.save()
    
    def get_unlocked_lessons(self):
        return Lesson.objects.filter(
            Q(prerequisite__isnull=True) |
            Q(prerequisite__in=self.get_completed_lessons())
        )
    

    
    @property
    def progress(self):
        total_lessons = Lesson.objects.count()
        if total_lessons == 0:
            return 0
        completed_lessons = 0  # Placeholder - replace with actual logic
        return int((completed_lessons / total_lessons) * 100)

    def __str__(self):
        return self.user.username

class Token(AuthToken):
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        return super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
class Exercise(models.Model):
    question = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)  # Remove default=
    updated_at = models.DateTimeField(auto_now=True) 
    
    def clean(self):
        # Add validation for different exercise types
        if self.exercise_type == 'word_with_audio' and not self.audio_url:
            raise ValidationError("Audio URL is required for word_with_audio exercises")
        if self.exercise_type == 'image_selection' and len(self.images) < 4:
            raise ValidationError("Image selection requires exactly 4 images")
    EXERCISE_TYPES = [
        ('word_with_audio', 'Word with Audio'),
        ('image_selection', 'Image Selection'),
        ('pronunciation', 'Pronunciation'),
        ('matching', 'Matching Quiz')
    ]
    
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='exercises'
    )
    exercise_type = models.CharField(
        max_length=20,
        choices=EXERCISE_TYPES
    )
    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=100)
    audio_url = models.URLField(blank=True, null=True)
    options = models.JSONField(default=list)
    images = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    xp_reward = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.lesson.title} - {self.get_exercise_type_display()}"
    

class LessonProgress(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='lesson_progresses'  # Changed from user_progress
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    is_completed = models.BooleanField(default=False)
    xp_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lesson', 'user')
        
    def __str__(self):
      username = self.user.username if self.user else "Unknown"
      lesson = self.lesson.title if self.lesson else "No Lesson"
      return f"{username} - {lesson}"

    
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('reminder', 'Reminder'),
        ('achievement', 'Achievement'),
        ('message', 'Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
class Community(models.Model):
    name = models.CharField(max_length=200)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name='communities')

    def __str__(self):
        return f"{self.name} ({self.language.name})"
    

class CommunityPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user = self.user.username if self.user else "Unknown User"
        community = self.community.name if self.community else "No Community"
        return f"Post by {user} in {community}"


    @property
    def is_member(self):
        # This will be used in the serializer
        return False  # Will be set dynamically in the view

    


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class WeeklyProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start = models.DateField()
    xp_earned = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'week_start')
class CommunityMessage(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        language_name = self.community.language.name if self.community and self.community.language else "No Language"
        return f"Message by {self.user.username} in {self.community.name} ({language_name})"
