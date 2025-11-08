# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from . import views, views_precios

router = DefaultRouter()
router.register(r'articulos', views.ArticuloViewSet, basename='articulo')
router.register(r'ordenes', views.OrdenViewSet, basename='orden')

# Rutas para Sistema de Gestión de Listas de Precios y Políticas Comerciales
router.register(r'empresas', views_precios.EmpresaViewSet, basename='empresa')
router.register(r'sucursales', views_precios.SucursalViewSet, basename='sucursal')
router.register(r'listas-precios', views_precios.ListaPrecioViewSet, basename='lista-precio')
router.register(r'precios-articulos', views_precios.PrecioArticuloViewSet, basename='precio-articulo')
router.register(r'reglas-precios', views_precios.ReglaPrecioViewSet, basename='regla-precio')
router.register(r'combinaciones-productos', views_precios.CombinacionProductoViewSet, basename='combinacion-producto')
router.register(r'descuentos-proveedor', views_precios.DescuentoProveedorViewSet, basename='descuento-proveedor')
router.register(r'calcular-precio', views_precios.CalcularPrecioViewSet, basename='calcular-precio')

urlpatterns = [
    # ViewSets (RESTful)
    path('', include(router.urls)),

    # Endpoints con Mixins / Genéricos (v1)
    path('v1/articulos/', views.ArticuloListCreateGeneric.as_view(), name='articulo-list-mixins'),
    path('v1/articulos/<uuid:pk>/', views.ArticuloDetailGeneric.as_view(), name='articulo-detail-mixins'),

    # Endpoints Genéricos simplificados (si los usas)
    path('v1/articulos/generic/', views.ArticuloListCreateSimple.as_view(), name='articulo-list-generic'),
    path('v1/articulos/generic/<uuid:pk>/', views.ArticuloDetailSimple.as_view(), name='articulo-detail-generic'),

    # JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
