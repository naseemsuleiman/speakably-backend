from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from datetime import datetime, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from rest_framework.authtoken.views import ObtainAuthToken
from .models import Language, Lesson, UserProfile, Unit, LessonProgress, Exercise
from .serializers import (
    LanguageSerializer, 
    LessonSerializer, 
    UserProfileSerializer, 
    UserSerializer,
    LoginSerializer,
     UnitSerializer
)
from rest_framework import serializers
from django.db.models import Prefetch, Exists, OuterRef

User = get_user_model()

class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Only keep one permission_classes

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': 'Failed to load languages', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# In views.py
# views.py
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related('unit', 'unit__language')
    serializer_class = LessonSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        language_id = self.request.query_params.get('language_id')
        unit_id = self.request.query_params.get('unit_id')
        
        if language_id:
            queryset = queryset.filter(unit__language_id=language_id)
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)
            
        return queryset.order_by('order')

    def perform_create(self, serializer):
        """Simplified to just handle the created_by field"""
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            request.data._mutable = True
            request.data.update({
                'lesson_type': request.data.get('type'),
                'audio_url': request.data.get('audioUrl'),
                'correct_option': request.data.get('correctOption'),
                'title': f"{request.data.get('word', 'Lesson')}",  # Safer title generation
            })
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': 'Failed to create lesson', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related('user', 'selected_language')
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
     return super().get_queryset()






    @action(detail=False, methods=['get'])
    def me(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to load profile', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=False, methods=['patch'])
    def update_preferences(self, request):
        """
        Update the current user's preferences
        """
        profile = UserProfile.objects.get(user=request.user)
        serializer = self.get_serializer(
            profile, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# views.py
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            
            # Check if username already exists
            username = serializer.validated_data.get('username')
            if User.objects.filter(username=username).exists():
                return Response(
                    {'username': 'A user with that username already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = serializer.save()
            
            # Create token
            token = Token.objects.create(user=user)
            
            # Create profile
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'daily_goal': 5,
                    'proficiency_level': 'beginner'
                }
            )
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# views.py
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                       context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            # Get or create profile with safe defaults
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'proficiency_level': 'beginner'
                    # Add other default fields if needed
                }
            )
            
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'profile': UserProfileSerializer(profile).data
            })
        except serializers.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class LogoutView(generics.GenericAPIView):
    """
    API endpoint for user logout
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Delete the token to logout
        request.auth.delete()
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK
        )
    
# In views.py
class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        proficiency = self.request.query_params.get('proficiency')
        language = self.request.query_params.get('language')
        
        if proficiency:
            queryset = queryset.filter(proficiency=proficiency)
        
        if language:
            queryset = queryset.filter(language_id=language)
        
        if self.request.query_params.get('include_lessons'):
            user = self.request.user
            queryset = queryset.prefetch_related(
                Prefetch(
                    'lessons',
                    queryset=Lesson.objects.all().order_by('order'),
                )
            )
            
            if user.is_authenticated:
                queryset = queryset.prefetch_related(
                    Prefetch(
                        'lessons__lesson_progresses',
                        queryset=LessonProgress.objects.filter(user=user),
                        to_attr='user_lesson_progress'
                    )
                )
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except serializers.ValidationError as e:
            return Response(
                {'error': str(e.detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UnitDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

# views.py
class UserProfileUpdateView(generics.UpdateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}
                
            return Response(serializer.data)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        



# Add this to all ViewSets
def handle_exception(self, exc):
    if isinstance(exc, (ValidationError, PermissionDenied)):
        return super().handle_exception(exc)
        
    return Response(
        {'error': 'An unexpected error occurred', 'detail': str(exc)},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


class ImageUploadView(generics.GenericAPIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in valid_extensions:
            return Response(
                {'error': 'Unsupported file type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"uploads/images/{timestamp}_{request.user.id}{ext}"
        
        try:
            # Save the file
            path = default_storage.save(filename, ContentFile(image_file.read()))
            full_url = request.build_absolute_uri(default_storage.url(path))
            
            return Response({
                'url': full_url,
                'path': path
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class AudioUploadView(generics.GenericAPIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if 'audio' not in request.FILES:
            return Response(
                {'error': 'No audio file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        audio_file = request.FILES['audio']
        
        # Validate file type
        valid_extensions = ['.mp3', '.wav', '.ogg']
        ext = os.path.splitext(audio_file.name)[1].lower()
        if ext not in valid_extensions:
            return Response(
                {'error': 'Unsupported file type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"uploads/audio/{timestamp}_{request.user.id}{ext}"
        
        try:
            # Save the file
            path = default_storage.save(filename, ContentFile(audio_file.read()))
            full_url = request.build_absolute_uri(default_storage.url(path))
            
            return Response({
                'url': full_url,
                'path': path
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# views.py
from django.db import transaction
from django.db.models import F
from .models import LessonProgress  # You'll need to create this model
# In views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_lesson(request, pk):
    try:
        with transaction.atomic():
            logger.info(f"Completing lesson {pk} for user {request.user.id}")
            
            lesson = Lesson.objects.get(pk=pk)
            xp_earned = int(request.data.get('xp_earned', 10))  # Ensure integer
            
            # Get or create user profile with defaults
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'daily_goal': 5,
                    'proficiency_level': 'beginner',
                    'xp': 0,
                    'daily_goal_completed': 0,
                    'current_streak': 0,
                    'last_activity_date': timezone.now().date()
                }
            )
            
            # Check for existing completion today
            today = timezone.now().date()
            existing = LessonProgress.objects.filter(
                lesson=lesson,
                user=request.user,
                completed_at__date=today
            ).first()
            
            if existing:
                return Response({
                    'status': 'already_completed',
                    'message': 'Lesson already completed today'
                })
            
            # Create progress record
            LessonProgress.objects.create(
                lesson=lesson,
                user=request.user,
                is_completed=True,
                xp_earned=xp_earned,
                completed_at=timezone.now()
            )
            
            # Update profile stats
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            
            # Streak logic
            if profile.last_activity_date == today:
                pass
            elif profile.last_activity_date == yesterday:
                profile.current_streak += 1

            else:
                profile.current_streak = 1

                
            
            profile.xp += xp_earned
            profile.daily_goal_completed += 1 
            profile.last_activity_date = today
            profile.save()
            
            # Refresh the profile to get updated values
            profile.refresh_from_db()
            
            return Response({
                'status': 'success',
                'xp_earned': xp_earned,
                'new_xp_total': profile.xp,
                'daily_goal_completed': profile.daily_goal_completed,
                'streak': profile.current_streak
            })
            
    except Exception as e:
        logger.exception(f"Error completing lesson {pk}")
        return Response({
            'error': str(e),
            'detail': "Server error completing lesson"
        }, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_user_progress(request):
    user = request.user

    # Delete lesson progress
    LessonProgress.objects.filter(user=user).delete()

    # Reset user profile fields
    try:
        profile = user.userprofile
        profile.daily_goal_completed = 0
        profile.current_streak = 0
        profile.last_activity_date = timezone.now().date()
        profile.last_streak_date = None
        profile.xp = 0
        profile.hearts = 5
        profile.gems = 0
        profile.save()

        return Response({'status': 'success', 'message': 'Progress reset successfully'})
    except UserProfile.DoesNotExist:
        return Response({'status': 'error', 'message': 'Profile not found'}, status=404)
    
    
    


from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        print("Fetched notifications for user:", self.request.user.username, "=", qs.count())
        return qs.order_by('-created_at')
