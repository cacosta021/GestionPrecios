"""
Servicio para gestionar la lógica de cálculo de precios
Sistema de Gestión de Listas de Precios y Políticas Comerciales
"""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from .models import (
    Empresa, Sucursal, ListaPrecio, PrecioArticulo, ReglaPrecio, 
    CombinacionProducto, Articulo, GrupoArticulo, LineaArticulo
)
from pos_project_acosta.choices import (
    EstadoEntidades, TipoReglaPrecio, CanalVenta, TipoDescuento
)


class PrecioService:
    """
    Servicio para calcular precios según listas de precios, reglas y combinaciones.
    Implementa la lógica jerárquica: precio base → canal → escala → monto → combinación → validación de costo → descuentos especiales
    """
    
    @staticmethod
    def obtener_lista_vigente(empresa_id=None, sucursal_id=None, fecha=None):
        """
        Obtener la lista de precios vigente para una empresa/sucursal en una fecha específica.
        
        Args:
            empresa_id: UUID de la empresa
            sucursal_id: UUID de la sucursal (opcional)
            fecha: Fecha para verificar vigencia (default: hoy)
        
        Returns:
            ListaPrecio vigente o None
        """
        if fecha is None:
            fecha = timezone.now().date()
        
        # Buscar lista por sucursal primero (más específica)
        if sucursal_id:
            try:
                sucursal = Sucursal.objects.get(sucursal_id=sucursal_id, estado=EstadoEntidades.ACTIVO)
                listas = ListaPrecio.objects.filter(
                    sucursal=sucursal,
                    estado=EstadoEntidades.ACTIVO
                )
                
                for lista in listas:
                    if lista.esta_vigente(fecha):
                        return lista
            except Sucursal.DoesNotExist:
                pass
        
        # Buscar lista por empresa
        if empresa_id:
            try:
                empresa = Empresa.objects.get(empresa_id=empresa_id, estado=EstadoEntidades.ACTIVO)
                listas = ListaPrecio.objects.filter(
                    empresa=empresa,
                    sucursal__isnull=True,
                    estado=EstadoEntidades.ACTIVO
                )
                
                for lista in listas:
                    if lista.esta_vigente(fecha):
                        return lista
            except Empresa.DoesNotExist:
                pass
        
        return None
    
    @staticmethod
    def calcular_precio(empresa_id, sucursal_id, articulo_id, canal=None, 
                       cantidad=1, monto_pedido=Decimal('0'), fecha=None):
        """
        Calcular el precio final de un artículo aplicando todas las reglas y políticas.
        
        Args:
            empresa_id: UUID de la empresa
            sucursal_id: UUID de la sucursal (opcional)
            articulo_id: UUID del artículo
            canal: Canal de venta (opcional)
            cantidad: Cantidad del artículo
            monto_pedido: Monto total del pedido
            fecha: Fecha para el cálculo (default: hoy)
        
        Returns:
            dict con precio_base, precio_final, reglas_aplicadas, autorizado_bajo_costo
        """
        if fecha is None:
            fecha = timezone.now().date()
        
        # Obtener lista vigente
        lista_precio = PrecioService.obtener_lista_vigente(empresa_id, sucursal_id, fecha)
        
        if not lista_precio:
            return {
                'precio_base': Decimal('0'),
                'precio_final': Decimal('0'),
                'reglas_aplicadas': [],
                'autorizado_bajo_costo': False,
                'error': 'No se encontró una lista de precios vigente'
            }
        
        # Obtener precio base del artículo
        try:
            precio_articulo = PrecioArticulo.objects.get(
                lista_precio=lista_precio,
                articulo_id=articulo_id
            )
            precio_base = precio_articulo.precio_base
            ultimo_costo = precio_articulo.ultimo_costo
            autorizado_bajo_costo = precio_articulo.autorizado_bajo_costo
        except PrecioArticulo.DoesNotExist:
            return {
                'precio_base': Decimal('0'),
                'precio_final': Decimal('0'),
                'reglas_aplicadas': [],
                'autorizado_bajo_costo': False,
                'error': 'No se encontró precio base para el artículo en esta lista'
            }
        
        # Obtener artículo para aplicar reglas
        try:
            articulo = Articulo.objects.get(articulo_id=articulo_id)
        except Articulo.DoesNotExist:
            return {
                'precio_base': precio_base,
                'precio_final': precio_base,
                'reglas_aplicadas': [],
                'autorizado_bajo_costo': autorizado_bajo_costo,
                'error': 'Artículo no encontrado'
            }
        
        # Aplicar reglas en orden de prioridad
        precio_final = precio_base
        reglas_aplicadas = []
        
        # Obtener reglas activas ordenadas por prioridad
        reglas = ReglaPrecio.objects.filter(
            lista_precio=lista_precio,
            estado=EstadoEntidades.ACTIVO
        ).order_by('prioridad', 'tipo_regla')
        
        for regla in reglas:
            precio_anterior = precio_final
            precio_final = PrecioService.aplicar_regla(
                regla, articulo, precio_final, canal, cantidad, monto_pedido
            )
            
            if precio_final != precio_anterior:
                reglas_aplicadas.append({
                    'regla_id': str(regla.regla_precio_id),
                    'nombre': regla.nombre,
                    'tipo': regla.get_tipo_regla_display(),
                    'precio_anterior': float(precio_anterior),
                    'precio_nuevo': float(precio_final),
                    'descuento_aplicado': float(precio_anterior - precio_final)
                })
        
        # Validar costo
        validacion_costo = PrecioService.validar_costo(precio_final, ultimo_costo, autorizado_bajo_costo)
        
        # Aplicar combinaciones de productos si aplica
        combinaciones = CombinacionProducto.objects.filter(
            lista_precio=lista_precio,
            estado=EstadoEntidades.ACTIVO
        )
        
        for combinacion in combinaciones:
            if PrecioService._aplica_combinacion(combinacion, articulo, cantidad):
                precio_anterior = precio_final
                precio_final = PrecioService._aplicar_combinacion(combinacion, precio_final)
                
                if precio_final != precio_anterior:
                    reglas_aplicadas.append({
                        'combinacion_id': str(combinacion.combinacion_id),
                        'nombre': combinacion.nombre,
                        'tipo': 'Combinación de Productos',
                        'precio_anterior': float(precio_anterior),
                        'precio_nuevo': float(precio_final),
                        'descuento_aplicado': float(precio_anterior - precio_final)
                    })
        
        return {
            'precio_base': float(precio_base),
            'precio_final': float(precio_final),
            'ultimo_costo': float(ultimo_costo),
            'reglas_aplicadas': reglas_aplicadas,
            'autorizado_bajo_costo': autorizado_bajo_costo,
            'validacion_costo': validacion_costo,
            'lista_precio_id': str(lista_precio.lista_precio_id),
            'lista_precio_nombre': lista_precio.nombre
        }
    
    @staticmethod
    def aplicar_regla(regla, articulo, precio_actual, canal=None, cantidad=1, monto_pedido=Decimal('0')):
        """
        Aplicar una regla de precio específica.
        
        Args:
            regla: Instancia de ReglaPrecio
            articulo: Instancia de Articulo
            precio_actual: Precio actual antes de aplicar la regla
            canal: Canal de venta
            cantidad: Cantidad del artículo
            monto_pedido: Monto total del pedido
        
        Returns:
            Precio después de aplicar la regla
        """
        # Verificar si la regla aplica al artículo
        if not PrecioService._regla_aplica_articulo(regla, articulo):
            return precio_actual
        
        precio_resultado = precio_actual
        
        # Aplicar según tipo de regla
        if regla.tipo_regla == TipoReglaPrecio.CANAL_VENTA:
            if canal and regla.canal_venta == canal:
                precio_resultado = PrecioService._aplicar_descuento(
                    precio_actual, regla.tipo_descuento, regla.valor_descuento
                )
        
        elif regla.tipo_regla == TipoReglaPrecio.ESCALA_UNIDADES:
            if PrecioService._cumple_escala_unidades(regla, cantidad):
                precio_resultado = PrecioService._aplicar_descuento(
                    precio_actual, regla.tipo_descuento, regla.valor_descuento
                )
        
        elif regla.tipo_regla == TipoReglaPrecio.ESCALA_MONTO:
            monto_item = precio_actual * cantidad
            if PrecioService._cumple_escala_monto(regla, monto_item):
                precio_resultado = PrecioService._aplicar_descuento(
                    precio_actual, regla.tipo_descuento, regla.valor_descuento
                )
        
        elif regla.tipo_regla == TipoReglaPrecio.MONTO_TOTAL_PEDIDO:
            if PrecioService._cumple_monto_total_pedido(regla, monto_pedido):
                precio_resultado = PrecioService._aplicar_descuento(
                    precio_actual, regla.tipo_descuento, regla.valor_descuento
                )
        
        return precio_resultado
    
    @staticmethod
    def validar_costo(precio_final, ultimo_costo, autorizado_bajo_costo):
        """
        Validar que el precio final no sea inferior al costo (a menos que esté autorizado).
        
        Returns:
            dict con validación y mensaje
        """
        if precio_final < ultimo_costo:
            if autorizado_bajo_costo:
                return {
                    'valido': True,
                    'mensaje': f'Precio bajo costo autorizado. Diferencia: {ultimo_costo - precio_final}',
                    'diferencia': float(ultimo_costo - precio_final)
                }
            else:
                return {
                    'valido': False,
                    'mensaje': f'Precio final ({precio_final}) es inferior al costo ({ultimo_costo}). No autorizado.',
                    'diferencia': float(ultimo_costo - precio_final)
                }
        else:
            return {
                'valido': True,
                'mensaje': 'Precio válido',
                'diferencia': float(precio_final - ultimo_costo)
            }
    
    @staticmethod
    def registrar_descuento_proveedor(precio_articulo_id, porcentaje_descuento, usuario, notas=None):
        """
        Registrar un descuento especial de proveedor.
        
        Args:
            precio_articulo_id: UUID del PrecioArticulo
            porcentaje_descuento: Porcentaje de descuento (50-70%)
            usuario: Usuario que autoriza
            notas: Notas adicionales
        
        Returns:
            Instancia de DescuentoProveedor creada
        """
        from .models import DescuentoProveedor
        
        try:
            precio_articulo = PrecioArticulo.objects.get(precio_articulo_id=precio_articulo_id)
        except PrecioArticulo.DoesNotExist:
            raise ValueError("PrecioArticulo no encontrado")
        
        # Calcular monto de descuento
        monto_descuento = precio_articulo.precio_base * (porcentaje_descuento / 100)
        
        descuento = DescuentoProveedor.objects.create(
            precio_articulo=precio_articulo,
            porcentaje_descuento=porcentaje_descuento,
            monto_descuento=monto_descuento,
            autorizado_por=usuario,
            notas=notas
        )
        
        # Actualizar precio_articulo
        precio_articulo.autorizado_bajo_costo = True
        precio_articulo.descuento_proveedor = porcentaje_descuento
        precio_articulo.save()
        
        return descuento
    
    # Métodos auxiliares privados
    
    @staticmethod
    def _regla_aplica_articulo(regla, articulo):
        """Verificar si una regla aplica a un artículo específico"""
        if regla.articulo and regla.articulo.articulo_id != articulo.articulo_id:
            return False
        
        if regla.linea and (not articulo.linea or regla.linea.linea_id != articulo.linea.linea_id):
            return False
        
        if regla.grupo and (not articulo.grupo or regla.grupo.grupo_id != articulo.grupo.grupo_id):
            return False
        
        return True
    
    @staticmethod
    def _cumple_escala_unidades(regla, cantidad):
        """Verificar si la cantidad cumple con la escala de unidades"""
        if regla.cantidad_minima and cantidad < regla.cantidad_minima:
            return False
        if regla.cantidad_maxima and cantidad > regla.cantidad_maxima:
            return False
        return True
    
    @staticmethod
    def _cumple_escala_monto(regla, monto):
        """Verificar si el monto cumple con la escala de monto"""
        if regla.monto_minimo and monto < regla.monto_minimo:
            return False
        if regla.monto_maximo and monto > regla.monto_maximo:
            return False
        return True
    
    @staticmethod
    def _cumple_monto_total_pedido(regla, monto_total):
        """Verificar si el monto total del pedido cumple con la regla"""
        if regla.monto_total_minimo and monto_total < regla.monto_total_minimo:
            return False
        if regla.monto_total_maximo and monto_total > regla.monto_total_maximo:
            return False
        return True
    
    @staticmethod
    def _aplicar_descuento(precio, tipo_descuento, valor_descuento):
        """Aplicar un descuento al precio"""
        if tipo_descuento == TipoDescuento.PORCENTAJE:
            return precio * (1 - valor_descuento / 100)
        elif tipo_descuento == TipoDescuento.MONTO_FIJO:
            return max(Decimal('0'), precio - valor_descuento)
        return precio
    
    @staticmethod
    def _aplica_combinacion(combinacion, articulo, cantidad):
        """Verificar si una combinación aplica a un artículo"""
        if combinacion.articulo and combinacion.articulo.articulo_id != articulo.articulo_id:
            return False
        
        if combinacion.linea and (not articulo.linea or combinacion.linea.linea_id != articulo.linea.linea_id):
            return False
        
        if combinacion.grupo and (not articulo.grupo or combinacion.grupo.grupo_id != articulo.grupo.grupo_id):
            return False
        
        if cantidad < combinacion.cantidad_minima_combinacion:
            return False
        
        if combinacion.cantidad_maxima_combinacion and cantidad > combinacion.cantidad_maxima_combinacion:
            return False
        
        return True
    
    @staticmethod
    def _aplicar_combinacion(combinacion, precio):
        """Aplicar el descuento de una combinación"""
        return PrecioService._aplicar_descuento(
            precio, combinacion.tipo_descuento, combinacion.valor_descuento
        )

