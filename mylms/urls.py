# File: project/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os
from django.http import JsonResponse, HttpResponse
import logging

logger = logging.getLogger(__name__)

def serve_react_app(request, app_name, path=''):
    logger.info(f"serve_react_app called with app_name: {app_name}, path: {path}")
    full_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, path)
    if os.path.exists(full_path):
        if full_path.endswith('.js') or full_path.endswith('.css'):
            with open(full_path, 'rb') as f:
                content = f.read()
            content_type = 'application/javascript' if full_path.endswith('.js') else 'text/css'
            return HttpResponse(content, content_type=content_type)
        return serve(request, os.path.basename(full_path), os.path.dirname(full_path))

    # If the exact file doesn't exist, serve index.html for client-side routing
    index_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r') as file:
            content = file.read()
        return HttpResponse(content, content_type='text/html')

    return HttpResponse("App not found", status=404)

def serve_static(request, app_name, path):
    logger.info(f"serve_react_app called with app_name: {app_name}, path: {path}")
    full_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'static', path)
    if os.path.exists(full_path):
        return serve(request, os.path.basename(full_path), os.path.dirname(full_path))
    return HttpResponse("App not found", status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('courses/', include('courses.urls')),
    path('sandbox/', include('sandbox.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    re_path(r'^deployed_apps/(?P<app_name>[^/]+)/(?P<path>.*)$', serve_react_app, name='serve_react_app'),
    re_path(r'^deployed_apps/(?P<app_name>[^/]+)/static/(?P<path>.*)$', serve_static, name='serve_static'),

    # Serve the React app's static files and index.html

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
