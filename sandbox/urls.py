from django.urls import path
from . import views

urlpatterns = [
    path('execute/', views.execute_code, name='execute'),
    path('execute-react/', views.execute_code, name='execute_react_code'),
    path('deploy/', views.deploy_component, name='deploy_component'),

]