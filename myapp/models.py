
from django.db import models
from django.contrib.auth.models import User

class Language(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Unit(models.Model):
    language = models.ForeignKey('Language', on_delete=models.CASCADE, related_name='units')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=50, default='📚')
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.language.name} - {self.title}"
    


class Lesson(models.Model):
    LESSON_TYPES = [
        ('vocabulary', 'Vocabulary'),
        ('grammar', 'Grammar'),
        ('listening', 'Listening'),
        ('speaking', 'Speaking'),
        ('practice', 'Practice'),
    ]
    
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPES)
    order = models.PositiveIntegerField(default=0)
    xp_reward = models.PositiveIntegerField(default=10)
    is_unlocked = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.unit.title} - {self.title}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    selected_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    proficiency_level = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username
