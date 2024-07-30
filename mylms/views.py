from django.shortcuts import render

def home_view(request):
    return render(request, 'index.html')  # Render a template named 'home.html'


# Create your views here.
