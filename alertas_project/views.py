# alertas_project/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User  # Añade esta línea
from django.contrib import messages
from alertas.forms import CustomUserCreationForm

def landing_page(request):
    """Vista para la página principal (landing page)."""
    return render(request, 'index.html')

# def login_view(request):
#     """Vista para el inicio de sesión."""
#     if request.method == 'POST':
#         form = AuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(username=username, password=password)
#             if user is not None:
#                 login(request, user)
#                 messages.info(request, f"Has iniciado sesión como {username}.")
#                 return redirect('alertas:alertas_list')
#             else:
#                 messages.error(request, "Usuario o contraseña inválidos.")
#         else:
#             messages.error(request, "Usuario o contraseña inválidos.")
    
#     form = AuthenticationForm()
#     return render(request, 'login.html', {'form': form})

def register_view(request):
    """Vista para el registro de usuarios con email como identificador principal."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # No guardar el usuario todavía
            user = form.save(commit=False)
            
            # Obtener el email y generar siempre un username a partir de él
            email = form.cleaned_data.get('email')
            
            # Generar username a partir del email
            base_username = email.split('@')[0]
            username = base_username
            
            # Asegurar que sea único
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Asignar el nombre de usuario generado
            user.username = username
            
            # Ahora sí guardar el usuario
            user.save()
            
            # Autenticar y loguear al usuario
            login(request, user)
            messages.success(request, f"¡Bienvenido, {user.first_name}! Tu cuenta ha sido creada con éxito.")
            
            # Redirigir al usuario a la página principal
            return redirect('alertas:alertas_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    """Vista para cerrar sesión y limpiar mensajes."""
    logout(request)
    
    # Limpiar mensajes
    storage = messages.get_messages(request)
    for message in storage:
        # Iterar sobre los mensajes los marca como "leídos"
        pass
    storage.used = True
    
    return redirect('login')