from django.contrib import admin
from .models import GrupoArticulo, LineaArticulo

# registramos nuestros modelos
admin.site.register(GrupoArticulo)
admin.site.register(LineaArticulo)
