from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

def serve_react_app(request, app_name):
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

    # Serve the React app's index.html
    re_path(r'^deployed/(?P<app_name>[^/]+)/$', serve_react_app, name='serve_react_app'),

    # Serve static files for the React app
    re_path(r'^deployed/(?P<path>.*)$', serve, {
        'document_root': settings.DEPLOYED_COMPONENTS_ROOT,
        'show_indexes': settings.DEBUG
    }),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
