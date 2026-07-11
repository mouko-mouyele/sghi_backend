from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path

from api.api import api
from sghi_backend.views import serve_favicon, serve_frontend_asset, serve_frontend_index

urlpatterns = [
    path('api/', api.urls),
    path('django-admin/', admin.site.urls),
    # Build Vite (npm run build) — assets à la racine comme dans index.html
    re_path(r'^assets/(?P<path>.*)$', serve_frontend_asset),
    path('favicon.svg', serve_favicon),
    # Vue Router — toutes les routes hors API renvoient index.html
    re_path(r'^(?!api/|django-admin/).*$', serve_frontend_index),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'SGHL — Administration'
admin.site.site_title = 'SGHL Admin'
admin.site.index_title = 'Tableau de bord hospitalier'
