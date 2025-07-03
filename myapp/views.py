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
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from datetime import datetime, timedelta
from django.utils import timezone
import logging
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncWeek
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import serializers
from django.db.models import Prefetch, Exists, OuterRef

from .models import (
    Language, 
    Lesson, 
    UserProfile, 
    Unit, 
    LessonProgress, 
    Exercise, 
    CommunityPost, 
    Notification, 
    CommunityMessage,
    Community
)
from .serializers import (
    LanguageSerializer, 
    LessonSerializer, 
    UserProfileSerializer, 
    UserSerializer,
    LoginSerializer,
    UnitSerializer,
    CommunityPostSerializer,
    NotificationSerializer,
    CommunitySerializer,
    CommunityMessageSerializer
)

logger = logging.getLogger(__name__)
User = get_user_model()

class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': 'Failed to load languages', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            request.data._mutable = True
            request.data.update({
                'lesson_type': request.data.get('type'),
                'audio_url': request.data.get('audioUrl'),
                'correct_option': request.data.get('correctOption'),
                'title': f"{request.data.get('word', 'Lesson')}",
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

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            
            username = serializer.validated_data.get('username')
            if User.objects.filter(username=username).exists():
                return Response(
                    {'username': 'A user with that username already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)

            
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

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                       context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'proficiency_level': 'beginner'
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
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK
        )

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

def check_proficiency_upgrade(self):
    completed_units = Unit.objects.filter(
        lessons__lesson_progresses__user=self.user,
        lessons__lesson_progresses__is_completed=True,
        proficiency=self.proficiency_level
    ).distinct().count()
    
    if completed_units >= 3:
        levels = ['beginner', 'intermediate', 'advanced']
        current_index = levels.index(self.proficiency_level)
        if current_index < len(levels) - 1:
            self.proficiency_level = levels[current_index + 1]
            self.save()
            return True
    return False

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
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in valid_extensions:
            return Response(
                {'error': 'Unsupported file type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"uploads/images/{timestamp}_{request.user.id}{ext}"
        
        try:
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
        valid_extensions = ['.mp3', '.wav', '.ogg']
        ext = os.path.splitext(audio_file.name)[1].lower()
        if ext not in valid_extensions:
            return Response(
                {'error': 'Unsupported file type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"uploads/audio/{timestamp}_{request.user.id}{ext}"
        
        try:
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_lesson(request, pk):
    try:
        with transaction.atomic():
            logger.info(f"Completing lesson {pk} for user {request.user.id}")
            
            lesson = Lesson.objects.get(pk=pk)
            xp_earned = int(request.data.get('xp_earned', 10))
            
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
            
            LessonProgress.objects.create(
                lesson=lesson,
                user=request.user,
                is_completed=True,
                xp_earned=xp_earned,
                completed_at=timezone.now()
            )
            
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            
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
    LessonProgress.objects.filter(user=user).delete()

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard_view(request):
    range_type = request.GET.get('range', 'week')
    user = request.user
    today = timezone.now().date()

    if range_type == 'day':
        start_date = today
    elif range_type == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif range_type == 'month':
        start_date = today.replace(day=1)
    else:
        return Response({"error": "Invalid range type"}, status=400)

    progress_qs = LessonProgress.objects.filter(completed_at__date__gte=start_date)
    leaderboard_data = (
        progress_qs
        .values('user')
        .annotate(total_xp=Sum('xp_earned'))
        .order_by('-total_xp')[:20]
    )

    leaderboard = []
    for entry in leaderboard_data:
        try:
            u = User.objects.get(id=entry['user'])
            profile = u.userprofile
            leaderboard.append({
                'user_id': u.id,
                'username': u.username,
                'xp_earned': entry['total_xp'],
                'language': {
                    'name': profile.selected_language.name if profile.selected_language else None,
                    'icon': profile.selected_language.flag if profile.selected_language else None,
                }
            })
        except UserProfile.DoesNotExist:
            continue

    user_total_xp = progress_qs.filter(user=user).aggregate(xp=Sum('xp_earned'))['xp'] or 0

    user_rank_qs = (
        progress_qs
        .values('user')
        .annotate(total_xp=Sum('xp_earned'))
        .order_by('-total_xp')
    )

    user_position = next(
        (i + 1 for i, entry in enumerate(user_rank_qs) if entry['user'] == user.id),
        None
    )

    user_profile = user.userprofile
    user_rank = {
        'position': user_position,
        'xp_earned': user_total_xp,
        'language': {
            'name': user_profile.selected_language.name if user_profile.selected_language else None,
            'icon': user_profile.selected_language.flag if user_profile.selected_language else None,
        },
        'next_level_xp': 1000
    }

    return Response({
        'leaderboard': leaderboard,
        'user_rank': user_rank
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_community(request):
    try:
        name = request.data.get('name')
        language_id = request.data.get('language')

        if not name:
            return Response({'error': 'Community name is required'}, status=400)
        if not language_id:
            return Response({'error': 'Language is required'}, status=400)

        language = get_object_or_404(Language, id=language_id)
        
        community = Community.objects.create(
            name=name,
            language=language,
            created_by=request.user
        )
        community.members.add(request.user)
        
        serializer = CommunitySerializer(community)
        return Response(serializer.data, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_post(request):
    content = request.data.get('content')
    language_id = request.data.get('language')
    
    if not content or not language_id:
        return Response({'error': 'Missing content or language'}, status=400)

    try:
        language = Language.objects.get(id=language_id)
        post = CommunityPost.objects.create(
            user=request.user, 
            content=content, 
            language=language
        )
        serializer = CommunityPostSerializer(post)
        return Response(serializer.data, status=201)
    except Language.DoesNotExist:
        return Response({'error': 'Invalid language'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_communities(request):
    try:
        communities = Community.objects.select_related('language', 'created_by').all()
        serializer = CommunitySerializer(communities, many=True, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching communities: {str(e)}")
        return Response({'error': 'Failed to load communities'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_communities(request):
    communities = Community.objects.filter(members=request.user)
    serializer = CommunitySerializer(communities, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_community_posts(request):
    language_id = request.query_params.get('language')
    
    posts = CommunityPost.objects.select_related('user', 'language').order_by('-created_at')
    
    if language_id:
        posts = posts.filter(language_id=language_id)
    
    serializer = CommunityPostSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_daily_reminders(request):
    if not request.user.is_staff:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    users_to_remind = User.objects.filter(
        userprofile__last_activity_date=yesterday,
        userprofile__daily_goal_completed__lt=F('userprofile__daily_goal')
    )
    
    for user in users_to_remind:
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
            
        except Exception as e:
            logger.error(f"Failed to send reminder to {user.email}: {str(e)}")
    
    return Response({'status': 'success', 'users_notified': users_to_remind.count()})

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    def patch(self, request, *args, **kwargs):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'success'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_languages(request):
    try:
        profile = UserProfile.objects.get(user=request.user)

        selected = profile.selected_language
        learning_languages = profile.learning_languages.all() if hasattr(profile, 'learning_languages') else []

        return Response({
            "selected_language": {
                "id": selected.id,
                "name": selected.name,
                "flag": selected.flag if selected else "🌍",
            } if selected else None,
            "learning_languages": [
                {
                    "id": lang.id,
                    "name": lang.name,
                    "flag": lang.flag or "🌍"
                } for lang in learning_languages
            ]
        })
    except UserProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_languages(request):
    profile = UserProfile.objects.get(user=request.user)

    selected_ids = request.data.get("selectedLanguages", [])
    primary_id = request.data.get("primaryLanguage", None)

    profile.learning_languages.clear()

    for lang_id in selected_ids:
        language = Language.objects.get(id=lang_id)
        is_primary = (lang_id == primary_id)
        profile.learning_languages.add(language, through_defaults={"is_primary": is_primary})

    if primary_id:
        profile.selected_language_id = primary_id
        profile.save()

    return Response({"message": "Languages updated"}, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_selected_language(request):
    language_id = request.data.get('selected_language_id')
    
    if not language_id:
        return Response({'error': 'No language ID provided'}, status=400)
    
    try:
        language = Language.objects.get(id=language_id)
        profile = UserProfile.objects.get(user=request.user)
        profile.selected_language = language
        profile.save()
        return Response({'status': 'success'})
    except Language.DoesNotExist:
        return Response({'error': 'Language not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_settings(request):
    profile = getattr(request.user, 'userprofile', None)
    if profile is None:
        return Response({"error": "User profile not found."}, status=404)

    return Response({
        "reminder_time": profile.reminder_time,
        "daily_reminder": profile.daily_reminder,
        "weekly_summary": profile.weekly_summary
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_notification_settings(request):
    profile = getattr(request.user, 'userprofile', None)
    if profile is None:
        return Response({"error": "User profile not found."}, status=404)

    try:
        data = request.data
        logger.info(f"Received data: {data}")

        if 'reminder_time' in data:
            profile.reminder_time = data['reminder_time']
        if 'daily_reminder' in data:
            profile.daily_reminder = data['daily_reminder']
        if 'weekly_summary' in data:
            profile.weekly_summary = data['weekly_summary']

        profile.save()

        return Response({
            "message": "Settings updated successfully",
            "reminder_time": profile.reminder_time,
            "daily_reminder": profile.daily_reminder,
            "weekly_summary": profile.weekly_summary
        })

    except Exception as e:
        logger.error(f"Update error: {e}")
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_community_members(request, pk):
    community = get_object_or_404(Community, pk=pk)
    members = community.members.select_related('userprofile').annotate(
        join_date=models.Min('community_members__created_at')
    ).order_by('username')
    
    data = []
    for member in members:
        data.append({
            'id': member.id,
            'username': member.username,
            'avatar': None,
            'join_date': member.join_date,
            'is_online': False
        })
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_community(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if community.members.filter(id=request.user.id).exists():
        return Response({'status': 'already_member'}, status=200)
    
    community.members.add(request.user)
    
    Notification.objects.create(
        user=request.user,
        title=f"Joined {community.name}",
        message=f"You've joined the {community.name} community",
        notification_type="community"
    )
    
    members = community.members.exclude(id=request.user.id)
    for member in members:
        Notification.objects.create(
            user=member,
            title="New member",
            message=f"{request.user.username} joined {community.name}",
            notification_type="community"
        )
    
    return Response({
        'status': 'success',
        'member_count': community.members.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_community(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if not community.members.filter(id=request.user.id).exists():
        return Response({'status': 'not_member'}, status=200)
    
    community.members.remove(request.user)
    
    members = community.members.all()
    for member in members:
        Notification.objects.create(
            user=member,
            title="Member left",
            message=f"{request.user.username} left {community.name}",
            notification_type="community"
        )
    
    return Response({
        'status': 'success',
        'member_count': community.members.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_community_messages(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if not community.members.filter(id=request.user.id).exists():
        return Response({'error': 'Not a member'}, status=403)
    
    messages = CommunityMessage.objects.filter(
        community=community
    ).select_related('user', 'reply_to', 'reply_to__user').order_by('created_at')
    serializer = CommunityMessageSerializer(messages, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_community_message(request, pk):
    community = get_object_or_404(Community, pk=pk)
    if not community.members.filter(id=request.user.id).exists():
        return Response({'error': 'Not a member'}, status=403)
    
    content = request.data.get('content')
    reply_to_id = request.data.get('reply_to')
    
    if not content:
        return Response({'error': 'Message content required'}, status=400)
    
    try:
        reply_to = None
        if reply_to_id:
            reply_to = CommunityMessage.objects.get(id=reply_to_id, community=community)
            
        message = CommunityMessage.objects.create(
            user=request.user,
            community=community,
            content=content,
            reply_to=reply_to
        )
        
        members = community.members.exclude(id=request.user.id)
        for member in members:
            Notification.objects.create(
                user=member,
                title=f"New message in {community.name}",
                message=f"{request.user.username}: {content[:50]}...",
                notification_type="message"
            )
        
        serializer = CommunityMessageSerializer(message)
        return Response(serializer.data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)