from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Language, Lesson, UserProfile , Unit
from .serializers import (
    LanguageSerializer, 
    LessonSerializer, 
    UserProfileSerializer, 
    UserSerializer,
    LoginSerializer,
     UnitSerializer
)
from rest_framework import serializers

User = get_user_model()

class LanguageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows languages to be viewed or edited.
    """
    permission_classes = [AllowAny] 
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter by user's selected language
        """
        queryset = super().get_queryset()
        # Add any custom filtering here if needed
        return queryset

# In views.py
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            # Log incoming data for debugging
            print("Incoming lesson data:", request.data)
            
            # Manually validate unit exists
            unit_id = request.data.get('unit')
            if not unit_id:
                return Response(
                    {'unit': 'This field is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if not Unit.objects.filter(id=unit_id).exists():
                return Response(
                    {'unit': 'Invalid unit ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return super().create(request, *args, **kwargs)
            
        except Exception as e:
            print("Lesson creation error:", str(e))
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows user profiles to be viewed or edited.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Users can only see their own profile unless they're admin
        """
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the current user's profile
        """
        profile = UserProfile.objects.get(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

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

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            token = Token.objects.create(user=user)
            UserProfile.objects.create(user=user)
            
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

class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Get or create user profile
        UserProfile.objects.get_or_create(user=user)
        
        response_data = {
            'user': UserSerializer(user).data,
            'token': token.key,
            'is_staff': user.is_staff  # Add this line to indicate admin status
        }
        
        return Response(response_data)
    
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
    
class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all().select_related('language')
    serializer_class = UnitSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        include_lessons = self.request.query_params.get('include_lessons', 'false').lower() == 'true'
        
        if include_lessons:
            queryset = queryset.prefetch_related('lessons')
        return queryset
    
class UnitDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

