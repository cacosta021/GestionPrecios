import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from pos_project_acosta.choices import (
    EstadoEntidades, EstadoOrden, TipoListaPrecio, 
    CanalVenta, TipoReglaPrecio, TipoDescuento
)
from django.conf import settings


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    documento = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clientes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Vendedor(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='vendedores',
        blank=True, null=True
    )
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class GrupoArticulo(models.Model):
    grupo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_grupo = models.CharField(max_length=5, null=False)
    nombre_grupo = models.CharField(max_length=150, null=False)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)

    class Meta:
        db_table = "grupos_articulos"
        ordering = ["codigo_grupo"]

    def __str__(self):
        return self.nombre_grupo


class LineaArticulo(models.Model):
    linea_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_linea = models.CharField(max_length=10, null=False)
    grupo = models.ForeignKey(GrupoArticulo, on_delete=models.RESTRICT, null=False, related_name='grupo_linea')
    nombre_linea = models.CharField(max_length=150, null=False)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)

    class Meta:
        db_table = "lineas_articulo"
        ordering = ["codigo_linea"]

    def __str__(self):
        return self.nombre_linea


class Articulo(models.Model):
    articulo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_articulo = models.CharField(max_length=30, unique=True)
    codigo_barras = models.CharField(max_length=50, null=True, blank=True)
    descripcion = models.CharField(max_length=200, null=False)
    presentacion = models.CharField(max_length=100, null=True, blank=True)
    grupo = models.ForeignKey(GrupoArticulo, on_delete=models.RESTRICT, null=True, blank=True)
    linea = models.ForeignKey(LineaArticulo, on_delete=models.RESTRICT, null=True, blank=True)
    stock = models.IntegerField(default=0)  # 🔹 AHORA ENTERO SIN DECIMALES
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)

    class Meta:
        db_table = "articulos"
        ordering = ["descripcion"]

    def __str__(self):
        return f"{self.codigo_articulo} - {self.descripcion}"


class PrecioArticuloAntiguo(models.Model):
    """
    Modelo antiguo de precios de artículos (mantenido para compatibilidad).
    Este modelo será reemplazado por el nuevo sistema de ListaPrecio y PrecioArticulo.
    """
    lista_precio_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='precios_antiguos')
    precio_1 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_2 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_3 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_4 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)

    class Meta:
        db_table = "listas_precios_antiguas"
        ordering = ["-lista_precio_id"]

    def __str__(self):
        return f"{self.articulo.descripcion} - P1: {self.precio_1}"


class OrdenCompraCliente(models.Model):
    pedido_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nro_pedido = models.BigIntegerField(unique=True, editable=False)
    fecha_pedido = models.DateField(auto_now_add=True, null=False)
    cliente = models.ForeignKey('Cliente', on_delete=models.RESTRICT, null=False)
    vendedor = models.ForeignKey('Vendedor', on_delete=models.RESTRICT, null=False)
    importe = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.IntegerField(choices=EstadoOrden, default=EstadoOrden.PENDIENTE)
    notas = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=False)

    def actualizar_total(self):
        total = sum(item.total_item for item in self.items_orden_compra.all())
        self.importe = total
        self.save()

    def __str__(self):
        return f"Orden #{self.nro_pedido} - {self.cliente}"

    class Meta:
        db_table = "ordenes_compra_cliente"
        ordering = ["-fecha_creacion"]


class ItemOrdenCompraCliente(models.Model):
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(OrdenCompraCliente, on_delete=models.CASCADE, null=False, related_name='items_orden_compra')
    nro_item = models.PositiveIntegerField(default=1, null=False)
    articulo = models.ForeignKey('Articulo', on_delete=models.RESTRICT, null=False, related_name='articulo_item_orden_compra')
    cantidad = models.PositiveIntegerField(null=False, default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    total_item = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=False)

    def save(self, *args, **kwargs):
        self.total_item = self.cantidad * self.precio_unitario

        if self.precio_unitario == 0:
            try:
                lista_precio = self.articulo.listaprecio
                self.precio_unitario = lista_precio.precio_1
                self.total_item = self.cantidad * self.precio_unitario
            except:
                pass
        super().save(*args, **kwargs)
        self.pedido.actualizar_total()

    def __str__(self):
        return f"{self.cantidad} x {self.articulo.descripcion}"

    class Meta:
        db_table = "items_ordenes_compra_cliente"


# ============================================================================
# MODELOS PARA SISTEMA DE GESTIÓN DE LISTAS DE PRECIOS Y POLÍTICAS COMERCIALES
# ============================================================================

class Empresa(models.Model):
    """Modelo para representar una empresa"""
    empresa_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_empresa = models.CharField(max_length=20, unique=True, null=False)
    nombre = models.CharField(max_length=200, null=False)
    ruc = models.CharField(max_length=20, unique=True, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Sucursal(models.Model):
    """Modelo para representar una sucursal de una empresa"""
    sucursal_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.RESTRICT, related_name='sucursales', null=False)
    codigo_sucursal = models.CharField(max_length=20, null=False)
    nombre = models.CharField(max_length=200, null=False)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sucursales"
        ordering = ["nombre"]
        unique_together = [['empresa', 'codigo_sucursal']]

    def __str__(self):
        return f"{self.empresa.nombre} - {self.nombre}"


class ListaPrecio(models.Model):
    """
    Modelo para representar una lista de precios.
    Cada empresa y sucursal pueden tener múltiples listas de precios.
    """
    lista_precio_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.RESTRICT, related_name='listas_precio', null=True, blank=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.RESTRICT, related_name='listas_precio', null=True, blank=True)
    nombre = models.CharField(max_length=200, null=False, default='Lista de Precios')
    tipo = models.IntegerField(choices=TipoListaPrecio, default=TipoListaPrecio.NORMAL)
    canal_venta = models.IntegerField(choices=CanalVenta, null=True, blank=True)
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    descripcion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True)
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listas_precios_nuevas"
        ordering = ["-fecha_inicio", "nombre"]
        indexes = [
            models.Index(fields=['empresa', 'sucursal', 'fecha_inicio', 'fecha_fin']),
            models.Index(fields=['estado', 'fecha_inicio', 'fecha_fin']),
        ]

    def clean(self):
        """Validar que no haya solapamiento de vigencias"""
        if self.empresa is None and self.sucursal is None:
            raise ValidationError("Debe especificar una empresa o una sucursal")
        
        if self.sucursal and self.empresa and self.sucursal.empresa != self.empresa:
            raise ValidationError("La sucursal debe pertenecer a la empresa especificada")
        
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio")
        
        # Validar solapamiento de vigencias
        if self.pk:
            listas_solapadas = ListaPrecio.objects.filter(
                empresa=self.empresa,
                sucursal=self.sucursal,
                estado=EstadoEntidades.ACTIVO
            ).exclude(pk=self.pk)
        else:
            listas_solapadas = ListaPrecio.objects.filter(
                empresa=self.empresa,
                sucursal=self.sucursal,
                estado=EstadoEntidades.ACTIVO
            )
        
        for lista in listas_solapadas:
            if lista.fecha_fin is None or lista.fecha_fin >= self.fecha_inicio:
                if self.fecha_fin is None or self.fecha_fin >= lista.fecha_inicio:
                    raise ValidationError(
                        f"Existe solapamiento de vigencias con la lista '{lista.nombre}' "
                        f"({lista.fecha_inicio} - {lista.fecha_fin or 'Sin fin'})"
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def esta_vigente(self, fecha=None):
        """Verificar si la lista está vigente en una fecha específica"""
        if fecha is None:
            fecha = timezone.now().date()
        
        if self.estado != EstadoEntidades.ACTIVO:
            return False
        
        if fecha < self.fecha_inicio:
            return False
        
        if self.fecha_fin and fecha > self.fecha_fin:
            return False
        
        return True

    def __str__(self):
        empresa_sucursal = f"{self.empresa.nombre if self.empresa else ''}"
        if self.sucursal:
            empresa_sucursal += f" - {self.sucursal.nombre}"
        return f"{self.nombre} ({empresa_sucursal})"


class PrecioArticulo(models.Model):
    """
    Modelo para representar el precio base de un artículo en una lista de precios.
    El precio base no puede ser inferior al último costo registrado.
    """
    precio_articulo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='precios_articulos', null=False)
    articulo = models.ForeignKey(Articulo, on_delete=models.RESTRICT, related_name='precios_articulos', null=False)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    ultimo_costo = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    autorizado_bajo_costo = models.BooleanField(default=False)
    descuento_proveedor = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                                             help_text="Descuento del proveedor (50-70%)")
    notas = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "precios_articulos"
        unique_together = [['lista_precio', 'articulo']]
        indexes = [
            models.Index(fields=['lista_precio', 'articulo']),
        ]

    def clean(self):
        """Validar que el precio base no sea inferior al último costo"""
        if self.precio_base < self.ultimo_costo:
            # Permitir bajo costo solo si está autorizado y tiene descuento de proveedor
            if not self.autorizado_bajo_costo:
                raise ValidationError(
                    f"El precio base ({self.precio_base}) no puede ser inferior al último costo ({self.ultimo_costo}). "
                    "Debe autorizar la venta bajo costo."
                )
            
            # Validar que el descuento del proveedor esté en el rango permitido (50-70%)
            if not self.descuento_proveedor or self.descuento_proveedor < 50 or self.descuento_proveedor > 70:
                raise ValidationError(
                    "Para ventas bajo costo, el descuento del proveedor debe estar entre 50% y 70%"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.articulo.descripcion} - {self.precio_base} ({self.lista_precio.nombre})"


class ReglaPrecio(models.Model):
    """
    Modelo para representar reglas de precio (políticas comerciales).
    Cada lista puede tener múltiples reglas: por canal, escalas, monto, combinación, etc.
    """
    regla_precio_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='reglas_precio', null=False)
    tipo_regla = models.IntegerField(choices=TipoReglaPrecio, null=False)
    nombre = models.CharField(max_length=200, null=False)
    prioridad = models.IntegerField(default=1, help_text="Prioridad de aplicación (menor número = mayor prioridad)")
    
    # Campos para canal de venta
    canal_venta = models.IntegerField(choices=CanalVenta, null=True, blank=True)
    
    # Campos para escalas de unidades
    cantidad_minima = models.PositiveIntegerField(null=True, blank=True)
    cantidad_maxima = models.PositiveIntegerField(null=True, blank=True)
    
    # Campos para escalas de monto
    monto_minimo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monto_maximo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Campos para monto total del pedido
    monto_total_minimo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monto_total_maximo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Tipo de descuento y valor
    tipo_descuento = models.IntegerField(choices=TipoDescuento, default=TipoDescuento.PORCENTAJE)
    valor_descuento = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    
    # Aplicación por grupo, línea o artículo específico
    grupo = models.ForeignKey(GrupoArticulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='reglas_precio')
    linea = models.ForeignKey(LineaArticulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='reglas_precio')
    articulo = models.ForeignKey(Articulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='reglas_precio')
    
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    descripcion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reglas_precios"
        ordering = ["prioridad", "tipo_regla"]
        indexes = [
            models.Index(fields=['lista_precio', 'tipo_regla', 'estado']),
            models.Index(fields=['prioridad', 'estado']),
        ]

    def clean(self):
        """Validar que los campos sean consistentes con el tipo de regla"""
        if self.tipo_regla == TipoReglaPrecio.CANAL_VENTA and not self.canal_venta:
            raise ValidationError("Debe especificar un canal de venta para este tipo de regla")
        
        if self.tipo_regla == TipoReglaPrecio.ESCALA_UNIDADES:
            if not self.cantidad_minima and not self.cantidad_maxima:
                raise ValidationError("Debe especificar al menos cantidad mínima o máxima para escalas de unidades")
            if self.cantidad_minima and self.cantidad_maxima and self.cantidad_minima > self.cantidad_maxima:
                raise ValidationError("La cantidad mínima no puede ser mayor que la máxima")
        
        if self.tipo_regla == TipoReglaPrecio.ESCALA_MONTO:
            if not self.monto_minimo and not self.monto_maximo:
                raise ValidationError("Debe especificar al menos monto mínimo o máximo para escalas de monto")
            if self.monto_minimo and self.monto_maximo and self.monto_minimo > self.monto_maximo:
                raise ValidationError("El monto mínimo no puede ser mayor que el máximo")
        
        if self.tipo_regla == TipoReglaPrecio.MONTO_TOTAL_PEDIDO:
            if not self.monto_total_minimo and not self.monto_total_maximo:
                raise ValidationError("Debe especificar al menos monto total mínimo o máximo")
            if self.monto_total_minimo and self.monto_total_maximo and self.monto_total_minimo > self.monto_total_maximo:
                raise ValidationError("El monto total mínimo no puede ser mayor que el máximo")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_regla_display()}) - Prioridad: {self.prioridad}"


class CombinacionProducto(models.Model):
    """
    Modelo para representar combinaciones de productos que aplican descuentos.
    Se pueden agrupar por grupo, línea o artículo específico.
    """
    combinacion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='combinaciones_productos', null=False)
    nombre = models.CharField(max_length=200, null=False)
    descripcion = models.TextField(null=True, blank=True)
    
    # Aplicación por grupo, línea o artículo
    grupo = models.ForeignKey(GrupoArticulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='combinaciones')
    linea = models.ForeignKey(LineaArticulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='combinaciones')
    articulo = models.ForeignKey(Articulo, on_delete=models.RESTRICT, null=True, blank=True, related_name='combinaciones')
    
    # Requisitos de la combinación
    cantidad_minima_combinacion = models.PositiveIntegerField(default=1, help_text="Cantidad mínima de productos en la combinación")
    cantidad_maxima_combinacion = models.PositiveIntegerField(null=True, blank=True, help_text="Cantidad máxima de productos en la combinación")
    
    # Descuento aplicado
    tipo_descuento = models.IntegerField(choices=TipoDescuento, default=TipoDescuento.PORCENTAJE)
    valor_descuento = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    
    estado = models.IntegerField(choices=EstadoEntidades, default=EstadoEntidades.ACTIVO)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "combinaciones_productos"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=['lista_precio', 'estado']),
        ]

    def clean(self):
        """Validar que se especifique al menos grupo, línea o artículo"""
        if not self.grupo and not self.linea and not self.articulo:
            raise ValidationError("Debe especificar al menos un grupo, línea o artículo")
        
        if self.cantidad_minima_combinacion and self.cantidad_maxima_combinacion:
            if self.cantidad_minima_combinacion > self.cantidad_maxima_combinacion:
                raise ValidationError("La cantidad mínima no puede ser mayor que la máxima")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_descuento_display()}: {self.valor_descuento}"


class DescuentoProveedor(models.Model):
    """
    Modelo para registrar descuentos especiales de proveedores.
    Se usa para autorizar ventas bajo costo.
    """
    descuento_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    precio_articulo = models.ForeignKey(PrecioArticulo, on_delete=models.CASCADE, related_name='descuentos_proveedor', null=False)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, null=False, 
                                              help_text="Porcentaje de descuento (50-70%)")
    monto_descuento = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=False, related_name='descuentos_autorizados')
    fecha_autorizacion = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "descuentos_proveedor"
        ordering = ["-fecha_autorizacion"]

    def clean(self):
        """Validar que el porcentaje esté en el rango permitido"""
        if self.porcentaje_descuento < 50 or self.porcentaje_descuento > 70:
            raise ValidationError("El porcentaje de descuento debe estar entre 50% y 70%")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Descuento {self.porcentaje_descuento}% - {self.precio_articulo.articulo.descripcion}"
