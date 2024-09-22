from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os
from django.http import JsonResponse, HttpResponse


def serve_react_app(request, app_name, file_path=''):
    if file_path:
        file_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, file_path)
        if os.path.exists(file_path):
            return serve(request, os.path.basename(file_path), os.path.dirname(file_path))

    index_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r') as file:
            content = file.read()
            return HttpResponse(content, content_type='text/html')
    return HttpResponse("App not found", status=404)


urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('courses/', include('courses.urls')),
                  path('sandbox/', include('sandbox.urls')),
                  path('', TemplateView.as_view(template_name='home.html'), name='home'),

                  # Serve the React app and its static files
                  re_path(r'^deployed/(?P<app_name>[^/]+)/(?P<file_path>.*)$', serve_react_app, name='serve_react_app'),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)