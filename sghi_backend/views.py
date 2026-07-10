import os
from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from django.http import FileResponse


def home(request):
    """Serve the Vite frontend index.html"""
    frontend_dist = os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html')
    
    if os.path.exists(frontend_dist):
        with open(frontend_dist, 'r', encoding='utf-8') as f:
            return FileResponse(f, content_type='text/html')
    else:
        # Fallback for development when frontend build doesn't exist
        return render(request, 'home.html')


class FrontendFallbackView(TemplateView):
    """
    Fallback view for Vue Router - serves index.html for all non-API routes
    This allows Vue Router to handle client-side routing
    """
    template_name = 'home.html'
    
    def get_template_names(self):
        frontend_dist = os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html')
        if os.path.exists(frontend_dist):
            return ['frontend/dist/index.html']
        return [self.template_name]

