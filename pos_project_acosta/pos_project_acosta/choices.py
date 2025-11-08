from django.db import models
class EstadoEntidades(models.IntegerChoices):
    ACTIVO = 1, "Activo"
    DE_BAJA = 9, "De baja"
    
class EstadoOrden(models.IntegerChoices):
    PENDIENTE = 1, "Pendiente"
    PROCESANDO = 2, "Procesando"
    COMPLETADA = 3, "Completada"
    CANCELADA = 4, "Cancelada"

class TipoListaPrecio(models.IntegerChoices):
    NORMAL = 1, "Normal"
    PROMOCIONAL = 2, "Promocional"
    ESPECIAL = 3, "Especial"

class CanalVenta(models.IntegerChoices):
    MOSTRADOR = 1, "Mostrador"
    MAYORISTA = 2, "Mayorista"
    MINORISTA = 3, "Minorista"
    ONLINE = 4, "Online"
    TELEFONICO = 5, "Telefónico"

class TipoReglaPrecio(models.IntegerChoices):
    CANAL_VENTA = 1, "Canal de Venta"
    ESCALA_UNIDADES = 2, "Escala de Unidades"
    ESCALA_MONTO = 3, "Escala de Monto"
    COMBINACION_PRODUCTOS = 4, "Combinación de Productos"
    MONTO_TOTAL_PEDIDO = 5, "Monto Total del Pedido"

class TipoDescuento(models.IntegerChoices):
    PORCENTAJE = 1, "Porcentaje"
    MONTO_FIJO = 2, "Monto Fijo"