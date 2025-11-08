"""
Vistas API para el Sistema de Gestión de Listas de Precios y Políticas Comerciales
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from core.services import PrecioService
from core.models import (
    Empresa, Sucursal, ListaPrecio, PrecioArticulo, ReglaPrecio,
    CombinacionProducto, DescuentoProveedor
)
from .serializers import (
    EmpresaSerializer, SucursalSerializer, ListaPrecioNuevaSerializer,
    PrecioArticuloSerializer, ReglaPrecioSerializer, CombinacionProductoSerializer,
    DescuentoProveedorSerializer, CalcularPrecioRequestSerializer, CalcularPrecioResponseSerializer
)
from pos_project_acosta.choices import EstadoEntidades


class EmpresaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar empresas
    """
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'empresa_id'

    def get_queryset(self):
        queryset = Empresa.objects.all()
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class SucursalViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar sucursales
    """
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'sucursal_id'

    def get_queryset(self):
        queryset = Sucursal.objects.all()
        empresa_id = self.request.query_params.get('empresa_id', None)
        estado = self.request.query_params.get('estado', None)
        
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class ListaPrecioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar listas de precios
    """
    queryset = ListaPrecio.objects.all()
    serializer_class = ListaPrecioNuevaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'lista_precio_id'

    def get_queryset(self):
        queryset = ListaPrecio.objects.all()
        empresa_id = self.request.query_params.get('empresa_id', None)
        sucursal_id = self.request.query_params.get('sucursal_id', None)
        estado = self.request.query_params.get('estado', None)
        vigente = self.request.query_params.get('vigente', None)
        
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        if sucursal_id:
            queryset = queryset.filter(sucursal_id=sucursal_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if vigente == 'true':
            fecha = timezone.now().date()
            queryset = [lista for lista in queryset if lista.esta_vigente(fecha)]
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=True, methods=['get'])
    def precios_articulos(self, request, lista_precio_id=None):
        """Obtener todos los precios de artículos de una lista"""
        lista_precio = self.get_object()
        precios = PrecioArticulo.objects.filter(lista_precio=lista_precio)
        serializer = PrecioArticuloSerializer(precios, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reglas(self, request, lista_precio_id=None):
        """Obtener todas las reglas de una lista"""
        lista_precio = self.get_object()
        reglas = ReglaPrecio.objects.filter(lista_precio=lista_precio)
        serializer = ReglaPrecioSerializer(reglas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def combinaciones(self, request, lista_precio_id=None):
        """Obtener todas las combinaciones de una lista"""
        lista_precio = self.get_object()
        combinaciones = CombinacionProducto.objects.filter(lista_precio=lista_precio)
        serializer = CombinacionProductoSerializer(combinaciones, many=True)
        return Response(serializer.data)


class PrecioArticuloViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar precios de artículos
    """
    queryset = PrecioArticulo.objects.all()
    serializer_class = PrecioArticuloSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'precio_articulo_id'

    def get_queryset(self):
        queryset = PrecioArticulo.objects.all()
        lista_precio_id = self.request.query_params.get('lista_precio_id', None)
        articulo_id = self.request.query_params.get('articulo_id', None)
        
        if lista_precio_id:
            queryset = queryset.filter(lista_precio_id=lista_precio_id)
        if articulo_id:
            queryset = queryset.filter(articulo_id=articulo_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)


class ReglaPrecioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reglas de precio
    """
    queryset = ReglaPrecio.objects.all()
    serializer_class = ReglaPrecioSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'regla_precio_id'

    def get_queryset(self):
        queryset = ReglaPrecio.objects.all()
        lista_precio_id = self.request.query_params.get('lista_precio_id', None)
        tipo_regla = self.request.query_params.get('tipo_regla', None)
        estado = self.request.query_params.get('estado', None)
        
        if lista_precio_id:
            queryset = queryset.filter(lista_precio_id=lista_precio_id)
        if tipo_regla:
            queryset = queryset.filter(tipo_regla=tipo_regla)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset.order_by('prioridad', 'tipo_regla')

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)


class CombinacionProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar combinaciones de productos
    """
    queryset = CombinacionProducto.objects.all()
    serializer_class = CombinacionProductoSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'combinacion_id'

    def get_queryset(self):
        queryset = CombinacionProducto.objects.all()
        lista_precio_id = self.request.query_params.get('lista_precio_id', None)
        estado = self.request.query_params.get('estado', None)
        
        if lista_precio_id:
            queryset = queryset.filter(lista_precio_id=lista_precio_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)


class DescuentoProveedorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar descuentos de proveedores
    """
    queryset = DescuentoProveedor.objects.all()
    serializer_class = DescuentoProveedorSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'descuento_id'

    def get_queryset(self):
        queryset = DescuentoProveedor.objects.all()
        precio_articulo_id = self.request.query_params.get('precio_articulo_id', None)
        
        if precio_articulo_id:
            queryset = queryset.filter(precio_articulo_id=precio_articulo_id)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        precio_articulo_id = serializer.validated_data['precio_articulo'].precio_articulo_id
        porcentaje_descuento = serializer.validated_data['porcentaje_descuento']
        
        # Registrar el descuento usando el servicio
        descuento = PrecioService.registrar_descuento_proveedor(
            precio_articulo_id=precio_articulo_id,
            porcentaje_descuento=porcentaje_descuento,
            usuario=self.request.user,
            notas=serializer.validated_data.get('notas')
        )
        serializer.instance = descuento


class CalcularPrecioViewSet(viewsets.ViewSet):
    """
    ViewSet para calcular precios aplicando todas las reglas y políticas
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def calcular(self, request):
        """
        Calcular el precio final de un artículo
        
        Request body:
        {
            "empresa_id": "uuid",
            "sucursal_id": "uuid" (opcional),
            "articulo_id": "uuid",
            "canal": 1 (opcional),
            "cantidad": 1,
            "monto_pedido": 0.00,
            "fecha": "2025-01-01" (opcional)
        }
        
        Response:
        {
            "precio_base": 100.00,
            "precio_final": 85.00,
            "ultimo_costo": 80.00,
            "reglas_aplicadas": [...],
            "autorizado_bajo_costo": false,
            "validacion_costo": {...},
            "lista_precio_id": "uuid",
            "lista_precio_nombre": "Lista Principal"
        }
        """
        serializer = CalcularPrecioRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            resultado = PrecioService.calcular_precio(
                empresa_id=data['empresa_id'],
                sucursal_id=data.get('sucursal_id'),
                articulo_id=data['articulo_id'],
                canal=data.get('canal'),
                cantidad=data.get('cantidad', 1),
                monto_pedido=Decimal(str(data.get('monto_pedido', 0))),
                fecha=data.get('fecha')
            )
            
            response_serializer = CalcularPrecioResponseSerializer(resultado)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def lista_vigente(self, request):
        """
        Obtener la lista de precios vigente para una empresa/sucursal
        
        Query params:
        - empresa_id: UUID de la empresa (requerido)
        - sucursal_id: UUID de la sucursal (opcional)
        - fecha: Fecha para verificar vigencia (opcional, default: hoy)
        """
        empresa_id = request.query_params.get('empresa_id', None)
        sucursal_id = request.query_params.get('sucursal_id', None)
        fecha_str = request.query_params.get('fecha', None)
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fecha = None
        if fecha_str:
            from datetime import datetime
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            lista = PrecioService.obtener_lista_vigente(
                empresa_id=empresa_id,
                sucursal_id=sucursal_id,
                fecha=fecha
            )
            
            if lista:
                serializer = ListaPrecioNuevaSerializer(lista)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'No se encontró una lista de precios vigente'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

