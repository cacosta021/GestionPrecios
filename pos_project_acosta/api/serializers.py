from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.http import Http404
from django.apps import apps
from pos_project_acosta.choices import EstadoOrden, EstadoEntidades

# ------------------------------------------------------------
# Helpers para resolver modelos dinámicamente sin importar módulos
# ------------------------------------------------------------
def _get_model(*candidates):
    """
    Recibe tuplas (app_label, ModelName) y retorna el primero que exista.
    Ej: _get_model(('api', 'Articulo'), ('core', 'Articulo'))
    """
    for app_label, model_name in candidates:
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            continue
    raise LookupError(f"No se encontró el modelo en candidatos: {candidates}")

# Aliases robustos (api primero; core como fallback)
Articulo              = _get_model(('api', 'Articulo'),              ('core', 'Articulo'))
ListaPrecio           = _get_model(('api', 'ListaPrecio'),           ('core', 'ListaPrecio'))
PrecioArticuloAntiguo = _get_model(('api', 'PrecioArticuloAntiguo'), ('core', 'PrecioArticuloAntiguo'))
GrupoArticulo         = _get_model(('api', 'GrupoArticulo'),         ('core', 'GrupoArticulo'))
LineaArticulo         = _get_model(('api', 'LineaArticulo'),         ('core', 'LineaArticulo'))
Cliente               = _get_model(('api', 'Cliente'),               ('core', 'Cliente'))
Vendedor              = _get_model(('api', 'Vendedor'),              ('core', 'Vendedor'))
OrdenCompraCliente    = _get_model(('api', 'OrdenCompraCliente'),    ('core', 'OrdenCompraCliente'))
ItemOrdenCompraCliente= _get_model(('api', 'ItemOrdenCompraCliente'),('core', 'ItemOrdenCompraCliente'))
Empresa               = _get_model(('api', 'Empresa'),               ('core', 'Empresa'))
Sucursal              = _get_model(('api', 'Sucursal'),              ('core', 'Sucursal'))
PrecioArticulo        = _get_model(('api', 'PrecioArticulo'),        ('core', 'PrecioArticulo'))
ReglaPrecio           = _get_model(('api', 'ReglaPrecio'),           ('core', 'ReglaPrecio'))
CombinacionProducto   = _get_model(('api', 'CombinacionProducto'),  ('core', 'CombinacionProducto'))
DescuentoProveedor    = _get_model(('api', 'DescuentoProveedor'),    ('core', 'DescuentoProveedor'))
#TipoIdentificacion    = _get_model(('api', 'TipoIdentificacion'),    ('core', 'TipoIdentificacion'))
#CanalCliente          = _get_model(('api', 'CanalCliente'),          ('core', 'CanalCliente'))

# ------------------------------------------------------------
# SERIALIZERS BASE (opcional; útil para validaciones personalizadas)
# ------------------------------------------------------------
class ArticuloPlainSerializer(serializers.Serializer):
    articulo_id = serializers.UUIDField(read_only=True)
    codigo_articulo = serializers.CharField(max_length=25)
    codigo_barras = serializers.CharField(max_length=25, required=False, allow_blank=True)
    descripcion = serializers.CharField(max_length=150)
    presentacion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    stock = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    grupo_id = serializers.UUIDField()
    linea_id = serializers.UUIDField()
    precio_1 = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    class Meta:
        model = Articulo
        fields = [
            'codigo_articulo', 'codigo_barras', 'descripcion',
            'presentacion', 'grupo_id', 'linea_id', 'stock', 'precio_1'
        ]

    def validate_codigo_articulo(self, value):
        if Articulo.objects.filter(codigo_articulo=value).exists():
            raise serializers.ValidationError("Este código de artículo ya existe.")
        if len(value) < 4:
            raise serializers.ValidationError("El código debe tener al menos 4 caracteres.")
        return value

    def validate_descripcion(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("La descripción es demasiado corta.")
        if len(value) > 150:
            raise serializers.ValidationError("La descripción no debe exceder los 150 caracteres.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo.")
        return value

    def validate(self, data):
        grupo_id = data.get('grupo_id')
        linea_id = data.get('linea_id')

        try:
            grupo = GrupoArticulo.objects.get(pk=grupo_id)
        except GrupoArticulo.DoesNotExist:
            raise serializers.ValidationError({"grupo_id": "El grupo seleccionado no existe."})

        try:
            linea = LineaArticulo.objects.get(pk=linea_id)
            if getattr(linea.grupo, 'grupo_id', None) != grupo_id:
                raise serializers.ValidationError({"linea_id": "La línea seleccionada no pertenece al grupo."})
        except LineaArticulo.DoesNotExist:
            raise serializers.ValidationError({"linea_id": "La línea seleccionada no existe."})

        return data

    def create(self, validated_data):
        return Articulo.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field in ['codigo_articulo', 'codigo_barras', 'descripcion', 'presentacion', 'stock']:
            setattr(instance, field, validated_data.get(field, getattr(instance, field)))
        instance.save()
        return instance

# ------------------------------------------------------------
# MODEL SERIALIZERS
# ------------------------------------------------------------
class GrupoArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoArticulo
        fields = ['grupo_id', 'codigo_grupo', 'nombre_grupo']

class LineaArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaArticulo
        fields = ['linea_id', 'codigo_linea', 'nombre_linea']

class ListaPrecioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo antiguo PrecioArticuloAntiguo (compatibilidad)"""
    class Meta:
        model = PrecioArticuloAntiguo
        fields = ['precio_1', 'precio_2', 'precio_3', 'precio_4', 'precio_compra', 'precio_costo']

class ArticuloSerializer(serializers.ModelSerializer):
    grupo = GrupoArticuloSerializer(read_only=True)
    linea = LineaArticuloSerializer(read_only=True)
    grupo_id = serializers.UUIDField(write_only=True)
    linea_id = serializers.UUIDField(write_only=True)
    precios = ListaPrecioSerializer(source='precios_antiguos', read_only=True, many=True)

    class Meta:
        model = Articulo
        fields = [
            'articulo_id', 'codigo_articulo', 'codigo_barras',
            'descripcion', 'presentacion', 'stock',
            'grupo', 'linea', 'grupo_id', 'linea_id', 'precios'
        ]

    def create(self, validated_data):
        grupo_id = validated_data.pop('grupo_id')
        linea_id = validated_data.pop('linea_id')
        grupo = GrupoArticulo.objects.get(pk=grupo_id)
        linea = LineaArticulo.objects.get(pk=linea_id)
        articulo = Articulo.objects.create(grupo=grupo, linea=linea, **validated_data)
        return articulo

class ArticuloListSerializer(serializers.ModelSerializer):
    grupo_nombre = serializers.CharField(source='grupo.nombre_grupo', read_only=True)
    linea_nombre = serializers.CharField(source='linea.nombre_linea', read_only=True)
    precio = serializers.SerializerMethodField()
    
    def get_precio(self, obj):
        """Obtener el precio del artículo desde el modelo antiguo"""
        precio_antiguo = obj.precios_antiguos.first()
        if precio_antiguo:
            return precio_antiguo.precio_1
        return None

    class Meta:
        model = Articulo
        fields = ['articulo_id', 'codigo_articulo', 'descripcion', 'grupo_nombre', 'linea_nombre', 'stock', 'precio']

# ------------------------------------------------------------
# SERIALIZER DINÁMICO (útil si quieres limitar campos con ?fields=)
# ------------------------------------------------------------
class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class ArticuloDynamicSerializer(DynamicFieldsModelSerializer):
    grupo = serializers.SlugRelatedField(slug_field='nombre_grupo', read_only=True)
    linea = serializers.SlugRelatedField(slug_field='nombre_linea', read_only=True)

    class Meta:
        model = Articulo
        fields = [
            'articulo_id', 'codigo_articulo', 'codigo_barras',
            'descripcion', 'presentacion', 'grupo', 'linea', 'stock'
        ]

# ------------------------------------------------------------
# ÓRDENES E ÍTEMS
# ------------------------------------------------------------
class ItemOrdenSerializer(serializers.ModelSerializer):
    articulo_descripcion = serializers.CharField(source='articulo.descripcion', read_only=True)

    class Meta:
        model = ItemOrdenCompraCliente
        fields = ['item_id', 'nro_item', 'articulo', 'articulo_descripcion', 'cantidad', 'precio_unitario', 'total_item']

class OrdenSerializer(serializers.ModelSerializer):
    items = ItemOrdenSerializer(source='item_orden_compra', many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombres', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = OrdenCompraCliente
        fields = [
            'pedido_id', 'nro_pedido', 'fecha_pedido', 'cliente',
            'cliente_nombre', 'vendedor', 'importe', 'estado',
            'estado_display', 'notas', 'items'
        ]

# ------------------------------------------------------------
# CREACIÓN DE ARTÍCULO (con validaciones y creación de lista de precios)
# ------------------------------------------------------------
class ArticuloCreateSerializer(serializers.ModelSerializer):
    grupo_id = serializers.UUIDField()
    linea_id = serializers.UUIDField()
    precio_1 = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)

    class Meta:
        model = Articulo
        fields = [
            'codigo_articulo', 'codigo_barras', 'descripcion',
            'presentacion', 'grupo_id', 'linea_id', 'stock', 'precio_1'
        ]

    def validate_codigo_articulo(self, value):
        if Articulo.objects.filter(codigo_articulo=value).exists():
            raise serializers.ValidationError("Este código de artículo ya existe.")
        return value

    def validate(self, data):
        grupo_id = data.get('grupo_id')
        linea_id = data.get('linea_id')
        try:
            linea = LineaArticulo.objects.get(pk=linea_id)
            if getattr(linea.grupo, 'grupo_id', None) != grupo_id:
                raise serializers.ValidationError({"linea_id": "La línea seleccionada no pertenece al grupo."})
        except LineaArticulo.DoesNotExist:
            raise serializers.ValidationError({"linea_id": "La línea seleccionada no existe."})
        return data

    def create(self, validated_data):
        precio_1 = validated_data.pop('precio_1')
        grupo_id = validated_data.pop('grupo_id')
        linea_id = validated_data.pop('linea_id')
        grupo = GrupoArticulo.objects.get(pk=grupo_id)
        linea = LineaArticulo.objects.get(pk=linea_id)

        import uuid
        articulo_id = uuid.uuid4()
        articulo = Articulo.objects.create(
            articulo_id=articulo_id, grupo=grupo, linea=linea, **validated_data
        )
        PrecioArticuloAntiguo.objects.create(articulo=articulo, precio_1=precio_1)
        return articulo

# ------------------------------------------------------------
# VISTAS FUNCIONALES (si aún las usas en api/urls.py)
# ------------------------------------------------------------
@api_view(['GET'])
def articulo_list(request):
    articulos = Articulo.objects.all()
    serializer = ArticuloListSerializer(articulos, many=True)
    return Response(serializer.data)

@api_view(['GET', 'PUT', 'DELETE'])
def articulo_detail(request, pk):
    try:
        articulo = Articulo.objects.get(pk=pk)
    except Articulo.DoesNotExist:
        return Response({"error": "Artículo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ArticuloSerializer(articulo)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = ArticuloSerializer(articulo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        articulo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def articulo_create(request):
    serializer = ArticuloCreateSerializer(data=request.data)
    if serializer.is_valid():
        articulo = serializer.save()
        return Response(ArticuloSerializer(articulo).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------------------------------
# CBV (si las expones en api/urls.py)
# ------------------------------------------------------------
class ArticuloListView(APIView):
    def get(self, request, format=None):
        articulos = Articulo.objects.all()
        serializer = ArticuloListSerializer(articulos, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = ArticuloCreateSerializer(data=request.data)
        if serializer.is_valid():
            articulo = serializer.save()
            return Response(ArticuloSerializer(articulo).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ArticuloDetailView(APIView):
    def get_object(self, pk):
        try:
            return Articulo.objects.get(pk=pk)
        except Articulo.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        articulo = self.get_object(pk)
        serializer = ArticuloSerializer(articulo)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        articulo = self.get_object(pk)
        serializer = ArticuloSerializer(articulo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        articulo = self.get_object(pk)
        articulo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ============================================================================
# SERIALIZERS PARA SISTEMA DE GESTIÓN DE LISTAS DE PRECIOS Y POLÍTICAS COMERCIALES
# ============================================================================

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            'empresa_id', 'codigo_empresa', 'nombre', 'ruc',
            'direccion', 'telefono', 'email', 'estado',
            'creado_en', 'actualizado_en'
        ]

class SucursalSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = Sucursal
        fields = [
            'sucursal_id', 'empresa', 'empresa_nombre', 'codigo_sucursal',
            'nombre', 'direccion', 'telefono', 'email', 'estado',
            'creado_en', 'actualizado_en'
        ]

class ListaPrecioNuevaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    canal_venta_display = serializers.CharField(source='get_canal_venta_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.username', read_only=True)
    
    class Meta:
        model = ListaPrecio
        fields = [
            'lista_precio_id', 'empresa', 'empresa_nombre', 'sucursal', 'sucursal_nombre',
            'nombre', 'tipo', 'tipo_display', 'canal_venta', 'canal_venta_display',
            'fecha_inicio', 'fecha_fin', 'estado', 'estado_display',
            'descripcion', 'creado_por', 'creado_por_nombre',
            'creado_en', 'actualizado_en'
        ]

class PrecioArticuloSerializer(serializers.ModelSerializer):
    articulo_descripcion = serializers.CharField(source='articulo.descripcion', read_only=True)
    articulo_codigo = serializers.CharField(source='articulo.codigo_articulo', read_only=True)
    lista_precio_nombre = serializers.CharField(source='lista_precio.nombre', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.username', read_only=True)
    
    class Meta:
        model = PrecioArticulo
        fields = [
            'precio_articulo_id', 'lista_precio', 'lista_precio_nombre',
            'articulo', 'articulo_descripcion', 'articulo_codigo',
            'precio_base', 'ultimo_costo', 'precio_compra',
            'autorizado_bajo_costo', 'descuento_proveedor', 'notas',
            'creado_por', 'creado_por_nombre', 'creado_en', 'actualizado_en'
        ]

class ReglaPrecioSerializer(serializers.ModelSerializer):
    lista_precio_nombre = serializers.CharField(source='lista_precio.nombre', read_only=True)
    tipo_regla_display = serializers.CharField(source='get_tipo_regla_display', read_only=True)
    canal_venta_display = serializers.CharField(source='get_canal_venta_display', read_only=True)
    tipo_descuento_display = serializers.CharField(source='get_tipo_descuento_display', read_only=True)
    grupo_nombre = serializers.CharField(source='grupo.nombre_grupo', read_only=True)
    linea_nombre = serializers.CharField(source='linea.nombre_linea', read_only=True)
    articulo_descripcion = serializers.CharField(source='articulo.descripcion', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.username', read_only=True)
    
    class Meta:
        model = ReglaPrecio
        fields = [
            'regla_precio_id', 'lista_precio', 'lista_precio_nombre',
            'tipo_regla', 'tipo_regla_display', 'nombre', 'prioridad',
            'canal_venta', 'canal_venta_display',
            'cantidad_minima', 'cantidad_maxima',
            'monto_minimo', 'monto_maximo',
            'monto_total_minimo', 'monto_total_maximo',
            'tipo_descuento', 'tipo_descuento_display', 'valor_descuento',
            'grupo', 'grupo_nombre', 'linea', 'linea_nombre',
            'articulo', 'articulo_descripcion',
            'estado', 'descripcion', 'creado_por', 'creado_por_nombre',
            'creado_en', 'actualizado_en'
        ]

class CombinacionProductoSerializer(serializers.ModelSerializer):
    lista_precio_nombre = serializers.CharField(source='lista_precio.nombre', read_only=True)
    tipo_descuento_display = serializers.CharField(source='get_tipo_descuento_display', read_only=True)
    grupo_nombre = serializers.CharField(source='grupo.nombre_grupo', read_only=True)
    linea_nombre = serializers.CharField(source='linea.nombre_linea', read_only=True)
    articulo_descripcion = serializers.CharField(source='articulo.descripcion', read_only=True)
    creado_por_nombre = serializers.CharField(source='creado_por.username', read_only=True)
    
    class Meta:
        model = CombinacionProducto
        fields = [
            'combinacion_id', 'lista_precio', 'lista_precio_nombre',
            'nombre', 'descripcion',
            'grupo', 'grupo_nombre', 'linea', 'linea_nombre',
            'articulo', 'articulo_descripcion',
            'cantidad_minima_combinacion', 'cantidad_maxima_combinacion',
            'tipo_descuento', 'tipo_descuento_display', 'valor_descuento',
            'estado', 'creado_por', 'creado_por_nombre',
            'creado_en', 'actualizado_en'
        ]

class DescuentoProveedorSerializer(serializers.ModelSerializer):
    precio_articulo_info = serializers.CharField(source='precio_articulo.articulo.descripcion', read_only=True)
    autorizado_por_nombre = serializers.CharField(source='autorizado_por.username', read_only=True)
    
    class Meta:
        model = DescuentoProveedor
        fields = [
            'descuento_id', 'precio_articulo', 'precio_articulo_info',
            'porcentaje_descuento', 'monto_descuento',
            'autorizado_por', 'autorizado_por_nombre',
            'fecha_autorizacion', 'notas'
        ]

# Serializer para el cálculo de precios
class CalcularPrecioRequestSerializer(serializers.Serializer):
    empresa_id = serializers.UUIDField(required=True)
    sucursal_id = serializers.UUIDField(required=False, allow_null=True)
    articulo_id = serializers.UUIDField(required=True)
    canal = serializers.IntegerField(required=False, allow_null=True)
    cantidad = serializers.IntegerField(default=1, min_value=1)
    monto_pedido = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, min_value=0)
    fecha = serializers.DateField(required=False, allow_null=True)

class CalcularPrecioResponseSerializer(serializers.Serializer):
    precio_base = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_final = serializers.DecimalField(max_digits=12, decimal_places=2)
    ultimo_costo = serializers.DecimalField(max_digits=12, decimal_places=2)
    reglas_aplicadas = serializers.ListField()
    autorizado_bajo_costo = serializers.BooleanField()
    validacion_costo = serializers.DictField()
    lista_precio_id = serializers.UUIDField()
    lista_precio_nombre = serializers.CharField()
    error = serializers.CharField(required=False, allow_null=True)
