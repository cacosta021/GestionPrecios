# api/throttling.py
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Articulo
from .serializers import ArticuloListSerializer

class BurstRateThrottle(AnonRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'


@api_view(['GET'])
def articulo_list(request):
    """
    Lista todos los artículos.
    """
    throttle_classes = [BurstRateThrottle]

    for throttle_class in throttle_classes:
        throttle = throttle_class()

        # El error está aquí, no debemos pasar 'self' sino 'view=None'
        if not throttle.allow_request(request, view=None):
            return Response(
                {"error": "Demasiadas solicitudes, intente más tarde."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

    articulos = Articulo.objects.all()
    serializer = ArticuloListSerializer(articulos, many=True)
    return Response(serializer.data)


# --- Mantengo solo una definición de ArticuloViewSet (la completa) ---
class ArticuloViewSet(viewsets.ModelViewSet):
    """
    Un viewset para ver y editar artículos.
    """
    queryset = Articulo.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grupo', 'linea', 'stock']
    search_fields = ['codigo_articulo', 'descripcion', 'codigo_barras']
    ordering_fields = ['codigo_articulo', 'descripcion', 'stock']
    throttle_classes = [SustainedRateThrottle]
