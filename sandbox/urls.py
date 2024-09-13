from django.urls import path, re_path
from . import views
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from .views import DeployToProductionView_dev, DeployToProductionView_prod
import os

urlpatterns = [
    path('check_container/', views.check_container, name='check_container'),
    path('execute/', views.check_or_create_container, name='execute_code'),
    path('stop_container/', views.stop_container, name='stop_container'),
    path('update_code/', views.update_code, name='update_code'),
    path('deploy_to_production/', DeployToProductionView_dev.as_view(), name='deploy_to_production'),
    path('deploy_to_server/', DeployToProductionView_prod.as_view(), name='deploy_to_server'),
    path('check_container_ready/', views.check_container_ready, name='check_container_ready'),
] + static(settings.DEPLOYED_COMPONENTS_URL, document_root=settings.DEPLOYED_COMPONENTS_ROOT)