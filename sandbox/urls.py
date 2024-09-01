from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('execute/', views.execute_code, name='execute_code'),
    path('deploy/', views.deploy_component, name='deploy_component'),
    path('test-docker/', views.test_docker, name='test_docker'),
    path('check_container_ready/', views.check_container_ready, name='check_container_ready'),

] + static(settings.DEPLOYED_COMPONENTS_URL, document_root=settings.DEPLOYED_COMPONENTS_ROOT)