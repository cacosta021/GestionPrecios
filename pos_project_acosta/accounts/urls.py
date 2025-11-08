from django.urls import path
from . import views
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.profile_view, name='profile'),
    path('perfil/actualizar/', views.profile_update, name='profile_update'),
    path('configuracion/', views.settings_view, name='settings'),
]