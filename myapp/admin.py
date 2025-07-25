from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Language,
    Unit,
    Lesson,
    Exercise,
    UserProfile,
    LessonProgress,
    Token,
    Community,
    CommunityPost,
    Comment,
    Notification,
    WeeklyProgress
)

# Unregister the default User admin
admin.site.unregister(User)

# Custom User Admin that includes UserProfile inline
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_selected_language', 'get_xp')
    list_select_related = ('userprofile',)
    
    def get_selected_language(self, instance):
        return instance.userprofile.selected_language
    get_selected_language.short_description = 'Language'
    
    def get_xp(self, instance):
        return instance.userprofile.xp
    get_xp.short_description = 'XP'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

admin.site.register(User, CustomUserAdmin)

# Community Admin
class CommunityPostInline(admin.TabularInline):
    model = CommunityPost
    extra = 1
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'created_by', 'created_at', 'member_count')
    list_filter = ('language',)
    search_fields = ('name', 'language__name', 'created_by__username')
    raw_id_fields = ('created_by', 'members')
    filter_horizontal = ('members',)
    inlines = (CommunityPostInline,)
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'

# Community Post Admin with Comment inline
class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'language', 'content_preview', 'created_at', 'comment_count')
    list_filter = ('language', 'community')
    search_fields = ('content', 'user__username', 'community__name')
    raw_id_fields = ('user', 'community')
    inlines = (CommentInline,)
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def comment_count(self, obj):
        return obj.comment_set.count()
    comment_count.short_description = 'Comments'

# Comment Admin
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post_preview', 'content_preview', 'created_at')
    list_filter = ('post__community',)
    search_fields = ('content', 'user__username', 'post__content')
    raw_id_fields = ('user', 'post')
    date_hierarchy = 'created_at'
    
    def post_preview(self, obj):
        return obj.post.content[:30] + '...' if len(obj.post.content) > 30 else obj.post.content
    post_preview.short_description = 'Post'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

# Notification Admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title_preview', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('title', 'message', 'user__username')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    list_editable = ('is_read',)
    
    def title_preview(self, obj):
        return obj.title[:30] + '...' if len(obj.title) > 30 else obj.title
    title_preview.short_description = 'Title'

# Weekly Progress Admin
@admin.register(WeeklyProgress)
class WeeklyProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start', 'xp_earned')
    list_filter = ('week_start',)
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
    date_hierarchy = 'week_start'

# Language Admin
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'speech_recognition_code', 'flag')
    search_fields = ('name', 'code')
    list_filter = ('code',)
    ordering = ('name',)

# Unit Admin with Lesson inline
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('title', 'lesson_type', 'order', 'is_unlocked', 'xp_reward')
    ordering = ('order',)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'proficiency', 'order', 'lesson_count')
    list_filter = ('language', 'proficiency')
    search_fields = ('title', 'language__name')
    inlines = (LessonInline,)
    ordering = ('language', 'order')
    
    def lesson_count(self, obj):
        return obj.lessons.count()
    lesson_count.short_description = 'Lessons'

# Exercise Admin with Lesson filter
@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('word', 'translation', 'exercise_type', 'lesson', 'order', 'xp_reward')
    list_filter = ('exercise_type', 'lesson__unit__language', 'lesson__unit')
    search_fields = ('word', 'translation', 'lesson__title')
    ordering = ('lesson__unit__language', 'lesson__unit', 'lesson', 'order')
    raw_id_fields = ('lesson',)

# Lesson Admin with Exercise inline
class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 1
    fields = ('exercise_type', 'word', 'translation', 'order', 'xp_reward')
    ordering = ('order',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'unit', 'lesson_type', 'order', 'is_unlocked', 'exercise_count', 'xp_reward')
    list_filter = ('lesson_type', 'unit__language', 'unit')
    search_fields = ('title', 'unit__title')
    inlines = (ExerciseInline,)
    ordering = ('unit__language', 'unit__order', 'order')
    
    def exercise_count(self, obj):
        return obj.exercises.count()
    exercise_count.short_description = 'Exercises'

# Lesson Progress Admin
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'is_completed', 'xp_earned', 'completed_at')
    list_filter = ('is_completed', 'lesson__unit__language', 'lesson__unit')
    search_fields = ('user__username', 'lesson__title')
    raw_id_fields = ('user', 'lesson')
    date_hierarchy = 'completed_at'
    ordering = ('-completed_at',)

# Token Admin
@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'created', 'expires_at', 'is_expired')
    fields = ('user', 'expires_at')
    ordering = ('-created',)
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'selected_language', 'proficiency_level', 'xp',
        'daily_goal', 'daily_goal_completed', 'current_streak',
        'last_activity_date', 'reminder_time', 'daily_reminder', 'weekly_summary'
    )
    list_filter = ('selected_language', 'proficiency_level', 'daily_reminder', 'weekly_summary')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    ordering = ('-xp',)

    fieldsets = (
        (None, {
            'fields': ('user', 'selected_language', 'proficiency_level')
        }),
        ('Progress', {
            'fields': ('xp', 'hearts', 'gems')
        }),
        ('Goals & Streaks', {
            'fields': (
                'daily_goal', 'daily_goal_completed',
                'current_streak', 'last_activity_date',
                'last_streak_date'
            )
        }),
        ('Reminders & Notifications', {
            'fields': ('reminder_time', 'daily_reminder', 'weekly_summary')
        }),
    )