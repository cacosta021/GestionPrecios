from django.shortcuts import render, redirect, get_object_or_404  
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from pos_project_acosta.choices import EstadoOrden, EstadoEntidades
import uuid

from .forms import ArticuloForm, PrecioArticuloAntiguoForm
from .cart import Cart

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------
def send_order_confirmation_email(orden):
    """Enviar email de confirmación de orden"""
    subject = f'Confirmación de Orden #{orden.nro_pedido}'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = orden.cliente.correo_electronico

    html_content = render_to_string('emails/order_confirmation.html', {
        'orden': orden,
        'items': orden.items_orden_compra.all(),
    })
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        [to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


# ------------------------------------------------------------
# VISTAS PRINCIPALES
# ------------------------------------------------------------
@login_required
def home(request):
    """Vista principal del dashboard"""
    from core.models import Articulo
    total_articulos = Articulo.objects.count()
    total_usuarios = User.objects.count()
    bajo_stock = Articulo.objects.filter(stock__lt=10).count()

    context = {
        'total_articulos': total_articulos,
        'total_usuarios': total_usuarios,
        'bajo_stock': bajo_stock,
        'ventas_hoy': 0,
    }
    return render(request, 'core/index.html', context)


# ------------------------------------------------------------
# ARTÍCULOS CRUD
# ------------------------------------------------------------
@login_required
def articulos_list(request):
    from core.models import Articulo
    articulos_list = Articulo.objects.all()

    q = request.GET.get('q')
    if q:
        articulos_list = articulos_list.filter(descripcion__icontains=q)

    paginator = Paginator(articulos_list, 15)
    page_number = request.GET.get('page')
    articulos = paginator.get_page(page_number)

    return render(request, 'core/articulos/list.html', {'articulos': articulos})


@login_required
def articulo_detail(request, articulo_id):
    from core.models import Articulo, PrecioArticuloAntiguo
    articulo = get_object_or_404(Articulo, articulo_id=articulo_id)
    lista_precio = PrecioArticuloAntiguo.objects.filter(articulo=articulo).first()  # 🔹 Modelo antiguo para compatibilidad

    if 'viewed_products' not in request.session:
        request.session['viewed_products'] = []
    producto_actual = str(articulo.articulo_id)
    viewed_products = request.session['viewed_products']

    if producto_actual in viewed_products:
        viewed_products.remove(producto_actual)
    viewed_products.insert(0, producto_actual)
    request.session['viewed_products'] = viewed_products[:5]
    request.session.modified = True

    recent_products = []
    if len(viewed_products) > 1:
        recent_uuids = [uuid.UUID(x) for x in viewed_products[1:6]]
        recent_products = Articulo.objects.filter(articulo_id__in=recent_uuids)

    return render(request, 'core/articulos/detail.html', {
        'articulo': articulo,
        'lista_precio': lista_precio,  # 🔹 NUEVO
        'recent_products': recent_products
    })


@login_required
def articulo_create(request):
    from core.models import PrecioArticuloAntiguo, Articulo
    if request.method == 'POST':
        form = ArticuloForm(request.POST)
        precio_form = PrecioArticuloAntiguoForm(request.POST)
        if form.is_valid() and precio_form.is_valid():
            try:
                articulo = form.save(commit=False)
                articulo.articulo_id = uuid.uuid4()
                articulo.save()

                lista_precio = precio_form.save(commit=False)
                lista_precio.articulo = articulo
                lista_precio.save()

                messages.success(request, f'¡Artículo "{articulo.descripcion}" creado correctamente!')
                return redirect('articulo_detail', articulo_id=articulo.articulo_id)
            except Exception as e:
                messages.error(request, f'Error al crear el artículo: {str(e)}')
        else:
            messages.warning(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ArticuloForm()
        precio_form = PrecioArticuloAntiguoForm()

    return render(request, 'core/articulos/form.html', {
        'form': form,
        'precio_form': precio_form
    })


@login_required
def articulo_edit(request, articulo_id):
    from .models import Articulo, LineaArticulo, GrupoArticulo, PrecioArticuloAntiguo
    articulo = get_object_or_404(Articulo, articulo_id=articulo_id)
    try:
        lista_precio = PrecioArticuloAntiguo.objects.get(articulo=articulo)
    except PrecioArticuloAntiguo.DoesNotExist:
        lista_precio = None

    if request.method == 'POST':
        form = ArticuloForm(request.POST, instance=articulo)
        if lista_precio:
            precio_form = PrecioArticuloAntiguoForm(request.POST, instance=lista_precio)
        else:
            precio_form = PrecioArticuloAntiguoForm(request.POST)
        
        if form.is_valid() and precio_form.is_valid():
            form.save()
            if lista_precio:
                precio_form.save()
            else:
                precio_nuevo = precio_form.save(commit=False)
                precio_nuevo.articulo = articulo
                precio_nuevo.save()
            messages.success(request, 'Artículo actualizado correctamente.')
            return redirect('articulo_detail', articulo_id=articulo.articulo_id)
    else:
        form = ArticuloForm(instance=articulo)
        if lista_precio:
            precio_form = PrecioArticuloAntiguoForm(instance=lista_precio)
        else:
            precio_form = PrecioArticuloAntiguoForm()

        # 🔹 Mostrar todas las líneas activas del grupo actual al editar
        if articulo.grupo:
            form.fields['linea'].queryset = LineaArticulo.objects.filter(
                grupo=articulo.grupo, estado=1
            )
        else:
            form.fields['linea'].queryset = LineaArticulo.objects.none()

    return render(request, 'core/articulos/form.html', {
        'form': form,
        'precio_form': precio_form
    })


@login_required
def articulo_delete(request, articulo_id):
    from core.models import Articulo
    articulo = get_object_or_404(Articulo, articulo_id=articulo_id)
    if request.method == 'POST':
        articulo.delete()
        messages.success(request, 'Artículo eliminado correctamente.')
        return redirect('articulos_list')
    return render(request, 'core/articulos/delete.html', {'articulo': articulo})


# ------------------------------------------------------------
# AJAX / CARRITO
# ------------------------------------------------------------
@login_required
def get_lineas_por_grupo(request, grupo_id):
    from core.models import LineaArticulo
    lineas = LineaArticulo.objects.filter(grupo_id=grupo_id, estado=1)
    data = [{'id': str(linea.linea_id), 'nombre': linea.nombre_linea} for linea in lineas]
    return JsonResponse(data, safe=False)


@require_POST
def cart_add(request, articulo_id):
    from core.models import Articulo
    cart = Cart(request)
    articulo = get_object_or_404(Articulo, articulo_id=articulo_id)
    cantidad = int(request.POST.get('cantidad', 1))
    update = request.POST.get('update')
    cart.add(articulo=articulo, cantidad=cantidad, update_cantidad=update)
    messages.success(request, f'"{articulo.descripcion}" añadido al carrito.')
    return redirect('cart_detail')


def cart_remove(request, articulo_id):
    from core.models import Articulo
    cart = Cart(request)
    articulo = get_object_or_404(Articulo, articulo_id=articulo_id)
    cart.remove(articulo)
    messages.info(request, f'"{articulo.descripcion}" eliminado del carrito.')
    return redirect('cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'core/cart/detail.html', {'cart': cart})


def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, 'Carrito vaciado correctamente.')
    return redirect('cart_detail')


# ------------------------------------------------------------
# CHECKOUT Y ÓRDENES
# ------------------------------------------------------------
@login_required
def checkout(request):
    from core.models import Cliente, Vendedor, OrdenCompraCliente, ItemOrdenCompraCliente, TipoIdentificacion, CanalCliente
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Tu carrito está vacío')
        return redirect('cart_detail')

    try:
        cliente = Cliente.objects.get(correo_electronico=request.user.email)
    except Cliente.DoesNotExist:
        try:
            tipo_id = TipoIdentificacion.objects.first()
            canal = CanalCliente.objects.first()
            cliente = Cliente.objects.create(
                cliente_id=uuid.uuid4(),
                tipo_identificacion=tipo_id,
                nro_documento=request.user.username[:11],
                nombres=request.user.get_full_name(),
                correo_electronico=request.user.email,
                canal=canal,
                estado=EstadoEntidades.ACTIVO
            )
        except Exception:
            messages.error(request, 'Error al procesar el cliente.')
            return redirect('cart_detail')

    vendedor = Vendedor.objects.first()
    if not vendedor:
        messages.error(request, 'No hay vendedores disponibles.')
        return redirect('cart_detail')

    if request.method == 'POST':
        try:
            orden = OrdenCompraCliente.objects.create(
                pedido_id=uuid.uuid4(),
                cliente=cliente,
                vendedor=vendedor,
                estado=EstadoOrden.PENDIENTE,
                notas=request.POST.get('notas', ''),
                creado_por=request.user
            )
            for item in cart:
                articulo = item['articulo']
                ItemOrdenCompraCliente.objects.create(
                    item_id=uuid.uuid4(),
                    pedido=orden,
                    nro_item=1,
                    articulo=articulo,
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio'],
                    creado_por=request.user
                )
            cart.clear()
            send_order_confirmation_email(orden)
            messages.success(request, f'¡Orden creada exitosamente! Nº {orden.nro_pedido}')
            return redirect('order_detail', pedido_id=orden.pedido_id)
        except Exception as e:
            messages.error(request, f'Error al procesar la orden: {str(e)}')
            return redirect('cart_detail')

    return render(request, 'core/cart/checkout.html', {
        'cart': cart,
        'cliente': cliente
    })


@login_required
def order_detail(request, pedido_id):
    from core.models import OrdenCompraCliente
    orden = get_object_or_404(OrdenCompraCliente, pedido_id=pedido_id)
    if orden.cliente.correo_electronico != request.user.email and not request.user.is_staff:
        messages.error(request, 'No tienes permiso para ver esta orden.')
        return redirect('home')
    return render(request, 'core/cart/order_detail.html', {'orden': orden})


@login_required
def articulos_catalogo(request):
    return render(request, 'core/articulos/list_infinite.html')


@login_required
def cancel_order(request, pedido_id):
    from core.models import OrdenCompraCliente
    orden = get_object_or_404(OrdenCompraCliente, pedido_id=pedido_id)

    if orden.cliente.correo_electronico != request.user.email and not request.user.is_staff:
        messages.error(request, 'No tienes permiso para cancelar esta orden.')
        return redirect('home')

    if orden.estado == EstadoOrden.COMPLETADA:
        messages.warning(request, 'No es posible cancelar una orden COMPLETADA.')
        return redirect('order_detail', pedido_id=pedido_id)

    if orden.estado == EstadoOrden.CANCELADA:
        messages.info(request, 'La orden ya estaba cancelada.')
        return redirect('order_detail', pedido_id=pedido_id)

    orden.estado = EstadoOrden.CANCELADA
    orden.save(update_fields=['estado'])
    messages.success(request, 'La orden fue cancelada correctamente.')
    return redirect('order_detail', pedido_id=pedido_id)


@login_required
def generate_pdf_order(request, pedido_id):
    from core.models import OrdenCompraCliente
    orden = get_object_or_404(OrdenCompraCliente, pedido_id=pedido_id)

    if orden.cliente.correo_electronico != request.user.email and not request.user.is_staff:
        messages.error(request, 'No tienes permiso para generar el PDF de esta orden.')
        return redirect('home')

    messages.info(request, 'Generación de PDF pendiente de implementación.')
    return redirect('order_detail', pedido_id=pedido_id)
