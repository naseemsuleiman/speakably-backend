# core/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Language, Lesson, UserProfile , Unit

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'language', 'title', 'order', 'icon']

# serializers.py
class LessonSerializer(serializers.ModelSerializer):
    unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        error_messages={
            'does_not_exist': 'The specified unit does not exist',
            'incorrect_type': 'Unit ID must be an integer'
        }
    )
    
    class Meta:
        model = Lesson
        fields = '__all__'
        extra_kwargs = {
            'title': {
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'blank': 'Title cannot be empty',
                    'required': 'Title is required'
                }
            },
            'content': {'required': False, 'allow_blank': True},
            'order': {'required': False, 'default': 0},
            'xp_reward': {'required': False, 'default': 10},
            'is_unlocked': {'required': False, 'default': True}
        }
        
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

class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    selected_language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.all(), allow_null=True)
    selected_language_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'selected_language', 'selected_language_name', 'proficiency_level']

    def get_user(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email,
            'date_joined': obj.user.date_joined,
            'last_login': obj.user.last_login,
            'is_active': obj.user.is_active
        }
    
    def get_selected_language_name(self, obj):
        return obj.selected_language.name if obj.selected_language else None


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