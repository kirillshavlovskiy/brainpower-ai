# File: project/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os
from django.http import HttpResponse, FileResponse
import logging
import mimetypes
logger = logging.getLogger(__name__)

def serve_react_app(request, app_name, path=''):
    if path.startswith('static/'):
        return serve_static(request, app_name, path)

    index_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r') as file:
            content = file.read()
        return HttpResponse(content, content_type='text/html')
    return HttpResponse("App not found", status=404)

def serve_static(request, app_name, path):
    full_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'static', path)
    if os.path.exists(full_path):
        content_type, encoding = mimetypes.guess_type(full_path)
        response = FileResponse(open(full_path, 'rb'), content_type=content_type)
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    return HttpResponse("Static file not found", status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('courses/', include('courses.urls')),
    path('sandbox/', include('sandbox.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    re_path(r'^(?P<app_name>[^/]+)(?P<path>/.*)?$', serve_react_app, name='serve_react_app'),
    # re_path(r'^deployed_apps/(?P<app_name>[^/]+)/static/(?P<path>.*)$', serve_static, name='serve_static'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
