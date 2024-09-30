"""mylms URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExecuteView, ThreadViewSet

router = DefaultRouter()
router.register(r'threads', ThreadViewSet, basename='thread')


urlpatterns = [
    path('add-content/', views.create_content, name='create-content'),
    path('show-content/', views.display_content, name='display_content'),
    path('process-content/<int:content_id>/', views.content_process_form, name='process_content'),
    path('lessons/<int:lesson_id>/', views.lesson_process_code, name='process_lesson'),
    path('process_code/', views.code_process_ai, name='process_code'),
    path('thread_start/', views.start_thread, name='start_thread'),
    path('chat_initialise/', views.chat, name='chat_code'),
    path('thread_retrieve/', views.retrieve_thread, name='retrieve_thread'),
    path('thread_save/', views.save_thread, name='save_thread'),
    path('agent-chat-start/', views.start_group_chat, name='start_chat_with_agent'),
    path('api/code_execute/', ExecuteView.as_view()),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('update_deployment_info/', views.update_deployment_info, name='update_deployment_info'),
    path('api/', include(router.urls)),
]
