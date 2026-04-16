from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('image/<path:path>', serve, {'document_root': BASE_DIR / 'image'}),
    ]
