# alertas_project/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages

def landing_page(request):
    """Vista para la página principal (landing page)."""
    return render(request, 'index.html')

def login_view(request):
    """Vista para el inicio de sesión."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Has iniciado sesión como {username}.")
                return redirect('alertas:alertas_list')
            else:
                messages.error(request, "Usuario o contraseña inválidos.")
        else:
            messages.error(request, "Usuario o contraseña inválidos.")
    
    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register_view(request):
    """Vista para el registro de usuarios."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro exitoso.")
            return redirect('alertas:alertas_list')
        else:
            messages.error(request, "Error en el registro. Por favor, verifica los datos.")
    else:
        form = UserCreationForm()
    
    return render(request, 'register.html', {'form': form})