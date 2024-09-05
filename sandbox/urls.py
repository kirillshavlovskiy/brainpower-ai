from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('check_container/', views.check_container, name='check_container'),
    path('execute/', views.check_or_create_container, name='execute_code'),
    path('stop_container/', views.stop_container, name='stop_container'),
    path('update_code/', views.update_code, name='update_code'),
    path('deploy/', views.deploy_component, name='deploy_component'),
    path('check_container_ready/', views.check_container_ready, name='check_container_ready'),

] + static(settings.DEPLOYED_COMPONENTS_URL, document_root=settings.DEPLOYED_COMPONENTS_ROOT)