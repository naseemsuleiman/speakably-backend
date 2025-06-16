# core/urls.py
from django.urls import path
from .views import (
    LanguageViewSet,
    LessonViewSet,
    UnitViewSet,
    UserProfileViewSet,
    RegisterView,
    LoginView,
    UnitDetailView
)

# Language endpoints
language_list = LanguageViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
language_detail = LanguageViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
# Lesson endpoints
lesson_list = LessonViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
lesson_detail = LessonViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# Unit endpoints
unit_list = UnitViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
unit_detail = UnitViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})


# Profile endpoints
profile_list = UserProfileViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
profile_detail = UserProfileViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
profile_me = UserProfileViewSet.as_view({
    'get': 'me'
})
profile_preferences = UserProfileViewSet.as_view({
    'patch': 'update_preferences'
})

urlpatterns = [
    # Language endpoints
    path('languages/', language_list, name='language-list'),
    path('languages/<int:pk>/', language_detail, name='language-detail'),
    
    # Lesson endpoints
    path('lessons/', lesson_list, name='lesson-list'),
    path('units/', unit_list, name = 'unit-list'),
    path('units/<int:pk>/', UnitDetailView.as_view(), name='unit-detail'),
    path('lessons/<int:pk>/', lesson_detail, name='lesson-detail'),
    
    # User Profile endpoints
    path('profiles/', profile_list, name='profile-list'),
    path('profiles/<int:pk>/', profile_detail, name='profile-detail'),
    path('profiles/me/', profile_me, name='profile-me'),
    path('profiles/update_preferences/', profile_preferences, name='profile-update-preferences'),
    
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
]