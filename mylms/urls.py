# File: project/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.views.static import serve as static_serve
import os
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

def serve_react_app(request, app_name, path=''):
    logger.debug(f"React app request: app_name={app_name}, path={path}")
    if path.startswith('/static/'):
        return serve_static(request, app_name, path[8:])  # Remove '/static/' from path

    # Serve index.html for all other routes
    index_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'index.html')
    logger.debug(f"Looking for index.html at: {index_path}")
    if os.path.exists(index_path):
        with open(index_path, 'r') as file:
            content = file.read()
        return HttpResponse(content, content_type='text/html')
    logger.error(f"Index file not found for app: {app_name}")
    return HttpResponse("App not found", status=404)


def serve_static(request, app_name, path):
    logger.debug(f"Static file request: app_name={app_name}, path={path}")
    full_path = os.path.join(
        settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'static', path
    )
    logger.debug(f"Constructed full_path: {full_path}")
    if os.path.exists(full_path):
        logger.debug(f"Static file exists: {full_path}")
        return static_serve(
            request, path, document_root=os.path.join(
                settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'static'
            )
        )
    logger.error(f"Static file not found at: {full_path}")
    return HttpResponse("Static file not found", status=404)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('courses/', include('courses.urls')),
    path('sandbox/', include('sandbox.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Serve the React app's static files and index.html
    re_path(
        r'^deployed_apps/(?P<app_name>[^/]+)/static/(?P<path>.*)$',
        serve_static, name='serve_static'
    ),
    re_path(
        r'^deployed_apps/(?P<app_name>[^/]+)(?P<path>/.*)?$',
        serve_react_app, name='serve_react_app'
    ),

]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
