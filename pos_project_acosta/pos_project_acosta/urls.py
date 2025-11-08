# pos_project_acosta/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Módulos de tu proyecto (URLs personalizadas primero para tener prioridad)
    path('accounts/', include('accounts.urls')),
    
    # Autenticación (allauth) - para otras funcionalidades como reset password, social login, etc.
    path('accounts/', include('allauth.urls')),

    path('', include('core.urls')),          # home y vistas del core
    path('api/', include('api.urls')),       # toda la API se maneja dentro de api/urls.py
]

# Archivos estáticos/media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
