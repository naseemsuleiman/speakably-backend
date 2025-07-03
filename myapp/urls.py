
from django import views
from django.urls import path
from .views import (
    LanguageViewSet,
    LessonViewSet,
    UnitViewSet,
    UserProfileViewSet,
    RegisterView,
    UnitDetailView,
    UserProfileUpdateView,
    ImageUploadView,
    complete_lesson,
    reset_user_progress,
    LogoutView,
    NotificationListView,
    leaderboard_view,
    my_languages,
    send_community_message,
    update_languages,
    update_selected_language,
    notification_settings,
    update_notification_settings,
    create_community,
    create_post,
    get_communities,
    join_community,
    get_user_communities,
    get_community_messages,
    get_community_members,
    leave_community
    
)
from .views import (
    
    get_community_posts,
    
    send_daily_reminders
)
from .views import CustomAuthToken


from django.http import JsonResponse

def root_view(request):
    return JsonResponse({"message": "Welcome to the API root."})

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
    path('', root_view), 
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
    path('login/', CustomAuthToken.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/profile/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('upload-image/', ImageUploadView.as_view(), name='upload-image'),
    path('lessons/<int:pk>/complete/', complete_lesson, name='complete-lesson'),
    path('profiles/reset/', reset_user_progress),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('community/posts/', get_community_posts, name='community-posts'),
    
    path('leaderboard/', leaderboard_view, name='leaderboard'),
    path('notifications/send-reminders/', send_daily_reminders, name='send-reminders'),
    path('my-languages/', my_languages, name='my_languages'),
    path('profiles/update-languages/', update_languages, name='update-languages'),
    path('profiles/update-selected-language/', update_selected_language, name='update-selected-language'),
    path('profiles/notification-settings/', notification_settings, name='notification-settings'),
    path('profiles/update-notification-settings/', update_notification_settings, name='update-notification-settings'),
    path('community/posts/create/', create_post, name='create-post'),
    path('community/create/', create_community, name='create-community'),
    path('community/', get_communities, name='community-list'),
    path('community/create/', create_community, name='create-community'),
    path('community/<int:pk>/join/', join_community, name='join-community'),
    path('community/user/', get_user_communities, name='user-communities'),
    path('community/<int:pk>/messages/', get_community_messages, name='community-messages'),
    path('community/<int:pk>/messages/send/', send_community_message, name='send-community-message'),
    path('communities/<int:pk>/members/', get_community_members, name='community-members'),
path('communities/<int:pk>/join/', join_community, name='join-community'),
path('communities/<int:pk>/leave/', leave_community, name='leave-community'),
path('communities/<int:pk>/messages/', get_community_messages, name='community-messages'),
path('communities/<int:pk>/messages/send/', send_community_message, name='send-community-message'),


]