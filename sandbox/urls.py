from django.urls import path, re_path
from . import views, views_next
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from .views import DeployToProductionView_dev, DeployToProductionView_prod
from django.http import HttpResponse
import os

urlpatterns = [
    path('get_container_logs/', views.get_container_logs, name='get_container_logs'),
    path('check_next_container/', views_next.check_container, name='check_next_container'),
    path('check_container/', views.check_container, name='check_container'),
    path('execute_next/', views_next.check_or_create_container, name='execute_next_code'),
    path('execute/', views.check_or_create_container, name='execute_code'),
    path('stop_container/', views.stop_container, name='stop_container'),
    path('update_code/', views.update_code, name='update_code'),
    path('deploy_to_production/', DeployToProductionView_dev.as_view(), name='deploy_to_production'),
    path('deploy_to_server/', DeployToProductionView_prod.as_view(), name='deploy_to_server'),
    path('check_container_ready/', views.check_container_ready, name='check_container_ready'),
    path('check_next_container_ready/', views_next.check_container_ready, name='check_next_container_ready'),
#    path('get_deployment_logs/', lambda request: HttpResponse(get_recent_logs(), content_type='text/plain')),

] + static(settings.DEPLOYED_COMPONENTS_URL, document_root=settings.DEPLOYED_COMPONENTS_ROOT)