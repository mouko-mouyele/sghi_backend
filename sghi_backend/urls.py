from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from api.api import api
from sghi_backend.views import home, FrontendFallbackView

urlpatterns = [
    path('api/', api.urls),
    path('django-admin/', admin.site.urls),  # admin technique Django (dev uniquement)
    
    # Serve frontend static files (CSS, JS, images from Vite build)
    re_path(r'^(?P<path>frontend/dist/.*)$', serve, {'document_root': settings.BASE_DIR}),
    
    # Frontend fallback for Vue Router - must be last
    re_path(r'^(?!api/|django-admin/).*$', FrontendFallbackView.as_view(), name='frontend'),
    path('', home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'SGHL — Administration'
admin.site.site_title = 'SGHL Admin'
admin.site.index_title = 'Tableau de bord hospitalier'
