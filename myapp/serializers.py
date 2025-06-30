# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Language, Lesson, UserProfile, Unit, Exercise, LessonProgress



class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = '__all__'
        extra_kwargs = {
            'lesson': {'required': False, 'write_only': True},
            'translation': {'required': False, 'allow_blank': True}
        }
    def validate(self, data):
        # Skip translation validation for matching exercises
        if data.get('exercise_type') != 'matching' and not data.get('translation'):
            raise serializers.ValidationError(
                {'translation': 'This field is required for non-matching exercises'}
            )
        
        # Validate image selection exercises
        if data.get('exercise_type') == 'image_selection':
            if len(data.get('images', [])) != 4:
                raise serializers.ValidationError(
                    {'images': 'Exactly 4 images required'}
                )
            if not any(img.get('is_correct') for img in data.get('images', [])):
                raise serializers.ValidationError(
                    {'images': 'At least one correct image required'}
                )
        
        return data
    
class ShallowUnitSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)

    class Meta:
        model = Unit
        fields = ['id', 'title', 'language', 'proficiency', 'icon', 'order']    


class LessonSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, required=False)
    is_completed = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()  # ✅ use method-based unit field

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'lesson_type', 'order',
            'exercises', 'is_completed', 'is_unlocked', 'xp_reward',
            'unit'
        ]

    def get_unit(self, obj):
        from .serializers import ShallowUnitSerializer  
        return ShallowUnitSerializer(obj.unit, context=self.context).data
    
    def get_is_completed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        if hasattr(obj, 'user_lesson_progress'):
            return any(p.is_completed for p in obj.user_lesson_progress)
            
        return LessonProgress.objects.filter(
            lesson=obj,
            user=request.user,
            is_completed=True
        ).exists()

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        if not obj.prerequisite:
            return True
            
        return LessonProgress.objects.filter(
            lesson=obj.prerequisite,
            user=request.user,
            is_completed=True
        ).exists()

    

class UnitSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, required=False)
    is_completed = serializers.SerializerMethodField()
    language_id = serializers.IntegerField(write_only=True)
    language = LanguageSerializer(read_only=True)
    class Meta:
        model = Unit
        fields = ['id', 'language_id', 'title', 'icon', 'order','language', 'proficiency', 'lessons', 'is_completed']

    def get_lessons(self, obj):
        lessons = obj.lessons.all()
        serializer = LessonSerializer(lessons, many=True, context=self.context)
        return serializer.data

    def get_language(self, obj):
        return {
            'id': obj.language.id,
            'name': obj.language.name,
            'code': obj.language.code,
            'speech_recognition_code': obj.language.speech_recognition_code,
            'flag': obj.language.flag
        }

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        return all(
            LessonProgress.objects.filter(
                lesson=lesson,
                user=request.user,
                is_completed=True
            ).exists()
            for lesson in obj.lessons.all()
        )

    def create(self, validated_data):
        lessons_data = validated_data.pop('lessons', [])
        unit = Unit.objects.create(**validated_data)
        
        for lesson_data in lessons_data:
            exercises_data = lesson_data.pop('exercises', [])
            lesson = Lesson.objects.create(unit=unit, **lesson_data)
            for exercise_data in exercises_data:
                Exercise.objects.create(lesson=lesson, **exercise_data)

        return unit

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add any additional processing here if needed
        return representation
    
    def validate(self, data):
        # Add any additional validation here
        lessons_data = data.get('lessons', [])
        
        for lesson in lessons_data:
            if 'lesson_type' not in lesson:
                raise serializers.ValidationError({
                    'lessons': 'Each lesson must have a lesson_type'
                })
            
            exercises_data = lesson.get('exercises', [])
            for exercise in exercises_data:
                if not exercise.get('word') and exercise.get('exercise_type') != 'matching':
                    raise serializers.ValidationError({
                        'exercises': 'Word is required for non-matching exercises'
                    })
        
        return data




# serializers.py

    


# serializers.py

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        error_messages={
            'min_length': 'Password must be at least 8 characters long.'
        }
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email is required.',
            'invalid': 'Enter a valid email address.'
        }
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'username': {
                'error_messages': {
                    'required': 'Username is required.',
                    'unique': 'This username is already taken.'
                }
            }
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

# serializers.py
# serializers.py
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    selected_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), 
        allow_null=True
    )
    selected_language_name = serializers.SerializerMethodField()
    selected_language_icon = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()  # Add this
    daily_goal_target = serializers.IntegerField(source='daily_goal')
    daily_goal_completed = serializers.SerializerMethodField()
    daily_goal_progress = serializers.SerializerMethodField()
    current_streak = serializers.IntegerField(read_only=True)
    

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'selected_language', 
            'selected_language_name', 'selected_language_icon',
            'proficiency_level', 'progress',  # Add progress
            'daily_goal_target', 'daily_goal_completed', 'daily_goal_progress',
            'current_streak'
        ]

    def get_user(self, obj):
        user = obj.user
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'last_login': user.last_login,
            'date_joined': user.date_joined 
        }
    
    def get_selected_language_name(self, obj):
        return obj.selected_language.name if obj.selected_language else None
    
    def get_selected_language_icon(self, obj):
        if not obj.selected_language:
            return None
        return getattr(obj.selected_language, 'flag', '🌐')  # Changed from icon to flag
    
    def get_progress(self, obj):
        total_lessons = Lesson.objects.filter(unit__language=obj.selected_language).count()
        if total_lessons == 0:
            return 0
        completed_lessons = LessonProgress.objects.filter(
            user=obj.user,
            is_completed=True,
            lesson__unit__language=obj.selected_language
        ).count()
        return int((completed_lessons / total_lessons) * 100) # Placeholder - replace with actual calculation # Default icon if missing

    def get_daily_goal_progress(self, obj):
        today = timezone.now().date()
        if obj.last_activity_date != today:
            # It's a new day → daily goal should be considered 0%
            return 0
        if obj.daily_goal == 0:
            return 0
        return round((obj.daily_goal_completed / obj.daily_goal) * 100)
    
    def get_daily_goal_completed(self, obj):
        today = timezone.now().date()
        if obj.last_activity_date != today:
         return 0
        return obj.daily_goal_completed

    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.last_activity_date != timezone.now().date():
         representation['daily_goal_completed'] = 0
        return representation



from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        label=_("Username"),
        write_only=True
    )
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username,
                                password=password)

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs
    


from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'created_at', 'notification_type', 'is_read']

    

