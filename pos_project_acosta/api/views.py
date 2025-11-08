from rest_framework import mixins, generics, viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from .pagination import CustomPagination
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly  # si no lo usas, puedes quitarlo

from .serializers import (
    ArticuloSerializer,
    ArticuloListSerializer,
    ArticuloCreateSerializer,
    ListaPrecioSerializer,
    OrdenSerializer,
)

# Helpers para no repetir código
def _articulo_model():
    """Devuelve el modelo asociado al ArticuloSerializer."""
    return ArticuloSerializer.Meta.model

def _orden_model():
    """Devuelve el modelo asociado al OrdenSerializer."""
    return OrdenSerializer.Meta.model


# ----------------------------------------------------------------------
# MIXINS Y VISTAS GENÉRICAS DE ARTÍCULOS
# ----------------------------------------------------------------------
class ArticuloListCreateGeneric(mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                generics.GenericAPIView):
    """
    Lista todos los artículos o crea uno nuevo usando mixins.
    Sin importar cómo se llame el modelo, se toma desde el serializer.
    """
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ArticuloCreateSerializer
        return ArticuloListSerializer

    def get_queryset(self):
        # Siempre toma el modelo desde el serializer
        Model = _articulo_model()
        return Model.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


class ArticuloDetailGeneric(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin,
                            generics.GenericAPIView):
    """
    Obtener, actualizar o eliminar un artículo usando mixins.
    """
    serializer_class = ArticuloSerializer

    def get_queryset(self):
        Model = _articulo_model()
        return Model.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


# ----------------------------------------------------------------------
# VISTAS GENÉRICAS SIMPLIFICADAS
# ----------------------------------------------------------------------
class ArticuloListCreateSimple(generics.ListCreateAPIView):
    """
    Lista todos los artículos o crea uno nuevo.
    Versión simplificada con vistas genéricas.
    """
    pagination_class = CustomPagination

    def get_queryset(self):
        Model = _articulo_model()
        return Model.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ArticuloCreateSerializer
        return ArticuloListSerializer


class ArticuloDetailSimple(generics.RetrieveUpdateDestroyAPIView):
    """
    Obtener, actualizar o eliminar un artículo.
    Versión simplificada con vistas genéricas.
    """
    serializer_class = ArticuloSerializer

    def get_queryset(self):
        Model = _articulo_model()
        return Model.objects.all()


# ----------------------------------------------------------------------
# VIEWSET DE ARTÍCULOS
# ----------------------------------------------------------------------
class ArticuloViewSet(viewsets.ModelViewSet):
    """
    ViewSet para ver y editar artículos.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['grupo', 'linea', 'stock']  # asegúrate de que existen en tu modelo
    search_fields = ['codigo_articulo', 'descripcion', 'codigo_barras']
    ordering_fields = ['codigo_articulo', 'descripcion', 'stock']
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        Model = _articulo_model()
        return Model.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ArticuloCreateSerializer
        elif self.action == 'list':
            return ArticuloListSerializer
        return ArticuloSerializer

    @action(detail=True, methods=['get'])
    def precios(self, request, pk=None):
        """
        Endpoint personalizado para obtener precios de un artículo.
        GET /api/articulos/{id}/precios/
        """
        articulo = self.get_object()
        # Intentamos acceder a la relación one-to-one/foreign-key si existe como 'listaprecio'
        lista_precio = getattr(articulo, 'listaprecio', None)
        if lista_precio is None:
            return Response({"error": "No hay lista de precios"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ListaPrecioSerializer(lista_precio)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """
        Endpoint personalizado para obtener artículos con bajo stock.
        GET /api/articulos/bajo_stock/
        """
        Model = _articulo_model()
        articulos = Model.objects.filter(stock__lt=10)
        serializer = ArticuloListSerializer(articulos, many=True)
        return Response(serializer.data)


# ----------------------------------------------------------------------
# VIEWSET DE ÓRDENES
# ----------------------------------------------------------------------
class OrdenViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver órdenes (solo lectura).
    """
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        Model = _orden_model()
        user = self.request.user
        if user.is_staff:
            return Model.objects.all()
        # Para usuarios normales, mostrar solo sus propias órdenes
        return Model.objects.filter(cliente__correo_electronico=user.email)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Endpoint para cancelar una orden.
        POST /api/ordenes/{id}/cancelar/
        """
        from pos_project_acosta.choices import EstadoOrden
        orden = self.get_object()

        if orden.estado != EstadoOrden.PENDIENTE:
            return Response(
                {"error": "Solo se pueden cancelar órdenes pendientes."},
                status=status.HTTP_400_BAD_REQUEST
            )

        orden.estado = EstadoOrden.CANCELADA
        orden.save(update_fields=['estado'])
        serializer = self.get_serializer(orden)
        return Response(serializer.data)
