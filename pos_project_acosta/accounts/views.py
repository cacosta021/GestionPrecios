from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import Usuario, Perfil


@login_required
def profile_view(request):
    """Vista para mostrar el perfil del usuario"""
    context = {
        'user': request.user,
    }
    return render(request, 'account/profile.html', context)


@login_required
def profile_update(request):
    """Vista para actualizar el perfil del usuario"""
    if request.method == 'POST':
        user = request.user

        # Validar y actualizar datos del usuario
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()

        # Validaciones básicas
        if not full_name:
            messages.error(request, 'El nombre completo es requerido.')
            return redirect('profile')
        
        if not email:
            messages.error(request, 'El correo electrónico es requerido.')
            return redirect('profile')

        # Verificar si el email ya existe en otro usuario
        if email != user.email:
            from .models import Usuario
            if Usuario.objects.filter(email=email).exclude(username=user.username).exists():
                messages.error(request, 'Este correo electrónico ya está en uso por otro usuario.')
                return redirect('profile')

        # Actualizar datos
        user.full_name = full_name
        user.email = email
        if mobile:
            user.mobile = mobile
        user.save()

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('profile')

    return redirect('profile')


@login_required
def settings_view(request):
    """Vista para la configuración del usuario (redirige al perfil por ahora)"""
    # Por ahora, la configuración es parte del perfil
    # Puedes expandir esto más adelante con más opciones
    return redirect('profile')


def login_view(request):
    """Vista para el login de usuarios"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Manejar tanto 'login' (allauth) como 'username' (Django)
        login_field = request.POST.get('login') or request.POST.get('username')
        password = request.POST.get('password')
        
        if login_field and password:
            # Intentar autenticar con username o email
            user = authenticate(request, username=login_field, password=password)
            
            # Si no funciona con username, intentar con email
            if user is None:
                try:
                    from .models import Usuario
                    user_obj = Usuario.objects.get(email=login_field)
                    user = authenticate(request, username=user_obj.username, password=password)
                except Usuario.DoesNotExist:
                    pass
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido, {user.full_name or user.username}!')
                
                # Manejar "remember me"
                if request.POST.get('remember'):
                    request.session.set_expiry(1209600)  # 2 semanas
                else:
                    request.session.set_expiry(0)  # Sesión de navegador
                
                # Redirigir a la página solicitada o a home
                next_page = request.GET.get('next') or request.POST.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect('home')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, complete todos los campos.')
    
    # Crear un formulario vacío para el template
    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()
    
    context = {
        'form': form,
        'next': request.GET.get('next', ''),
    }
    return render(request, 'account/login.html', context)


def logout_view(request):
    """Vista para cerrar sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')
