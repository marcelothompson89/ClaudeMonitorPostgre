# alertas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from alertas.forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm

import json
import datetime

from .models import Alerta, User, Keyword, EmailAlertConfig
from .forms import AlertaFilterForm, KeywordForm, EmailAlertConfigForm

@login_required
def get_keywords_for_user(request):
    """Vista AJAX para obtener las palabras clave de un usuario específico."""
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'keywords': []})
    
    keywords = Keyword.objects.filter(user_id=user_id, active=True).values_list('word', flat=True)
    return JsonResponse({'keywords': list(keywords)})

@login_required
def alertas_list(request):
    # Inicializar el formulario con los valores por defecto
    form = AlertaFilterForm(request.GET or None)
    
    # Obtener todas las alertas inicialmente
    alertas_query = Alerta.objects.all().order_by('-presentation_date')
    
    # Verificar si el filtro por palabras clave está activo
    keyword_filter_active = request.session.get('keyword_filter_active', False)
    
    # Aplicar filtros si se proporcionan
    if request.GET:
        # Filtro por institución
        institution = request.GET.get('institution')
        if institution:
            alertas_query = alertas_query.filter(institution=institution)
        
        # Filtro por país
        country = request.GET.get('country')
        if country:
            alertas_query = alertas_query.filter(country=country)
        
        # Filtro por tipo de fuente (nuevo)
        source_type = request.GET.get('source_type')
        if source_type:
            alertas_query = alertas_query.filter(source_type=source_type)
        
        # Filtro por categoría (nuevo)
        category = request.GET.get('category')
        if category:
            alertas_query = alertas_query.filter(category=category)
        
        # Filtro por rango de fechas
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
            # Incluir registros con fecha nula o dentro del rango
            alertas_query = alertas_query.filter(
                Q(presentation_date__isnull=True) |
                Q(presentation_date__range=[start_date, end_date])
            )
        
        # Búsqueda por texto
        search_text = request.GET.get('search_text')
        if search_text:
            alertas_query = alertas_query.filter(
                Q(title__icontains=search_text) |
                Q(description__icontains=search_text)
            )
        
        # Filtro por usuario y palabras clave seleccionadas en el formulario
        user_id = request.GET.get('user')
        if user_id:
            selected_keywords = request.GET.getlist('keywords')
            if selected_keywords:
                keyword_conditions = Q()
                for kw in selected_keywords:
                    keyword_conditions |= Q(title__icontains=kw) | Q(description__icontains=kw)
                
                alertas_query = alertas_query.filter(keyword_conditions)
    
    # Aplicar filtro automático por palabras clave del usuario actual si está activo
    if keyword_filter_active:
        user_keywords = Keyword.objects.filter(user=request.user, active=True).values_list('word', flat=True)
        if user_keywords:
            keyword_conditions = Q()
            for kw in user_keywords:
                keyword_conditions |= Q(title__icontains=kw) | Q(description__icontains=kw)
            
            alertas_query = alertas_query.filter(keyword_conditions)
    
    # Paginación (valor fijo de 30 registros por página)
    page_size = 30
    paginator = Paginator(alertas_query, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Configurar dinámicamente las opciones de keywords si se seleccionó un usuario
    if request.GET.get('user'):
        user_id = request.GET.get('user')
        keywords = Keyword.objects.filter(user_id=user_id, active=True).values_list('word', flat=True)
        form.fields['keywords'].choices = [(kw, kw) for kw in keywords]
    
    # Obtener fechas mínima y máxima para los filtros de fecha
    min_date = Alerta.objects.filter(presentation_date__isnull=False).order_by('presentation_date').first()
    max_date = Alerta.objects.filter(presentation_date__isnull=False).order_by('-presentation_date').first()
    
    min_date = min_date.presentation_date if min_date else timezone.now()
    max_date = max_date.presentation_date if max_date else timezone.now()
    
    # Obtener las palabras clave del usuario actual para mostrar en la interfaz
    user_keywords = Keyword.objects.filter(user=request.user, active=True)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_alertas': alertas_query.count(),
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'user_keywords': user_keywords,
        'keyword_filter_active': keyword_filter_active,
    }
    
    return render(request, 'alertas/alertas_list.html', context)

@login_required
def manage_keywords(request):
    """Vista para gestionar las palabras clave del usuario."""
    # Obtener las palabras clave del usuario actual
    keywords = Keyword.objects.filter(user=request.user).order_by('-created_at')
    
    # Manejar el formulario para añadir nueva palabra clave
    if request.method == 'POST':
        form = KeywordForm(request.POST)
        if form.is_valid():
            keyword = form.save(commit=False)
            keyword.user = request.user
            
            # Verificar si ya existe la palabra clave para este usuario
            if Keyword.objects.filter(user=request.user, word=keyword.word).exists():
                messages.warning(request, f'La palabra clave "{keyword.word}" ya existe en tu lista.')
            else:
                keyword.save()
                messages.success(request, f'Palabra clave "{keyword.word}" añadida correctamente.')
            
            return redirect('alertas:manage_keywords')
    else:
        form = KeywordForm()
    
    context = {
        'keywords': keywords,
        'form': form
    }
    
    return render(request, 'alertas/manage_keywords.html', context)

@login_required
@require_POST
def toggle_keyword_status(request, keyword_id):
    """Vista para activar/desactivar una palabra clave."""
    keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    keyword.active = not keyword.active
    keyword.save()
    
    status = "activada" if keyword.active else "desactivada"
    messages.success(request, f'Palabra clave "{keyword.word}" {status} correctamente.')
    
    # Si es una solicitud AJAX, devolver un JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'active': keyword.active,
            'keyword_id': keyword.id
        })
    
    return redirect('alertas:manage_keywords')

@login_required
@require_POST
def delete_keyword(request, keyword_id):
    """Vista para eliminar una palabra clave."""
    keyword = get_object_or_404(Keyword, id=keyword_id, user=request.user)
    word = keyword.word
    keyword.delete()
    
    messages.success(request, f'Palabra clave "{word}" eliminada correctamente.')
    
    # Si es una solicitud AJAX, devolver un JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('alertas:manage_keywords')

@login_required
def toggle_keyword_filter(request):
    """Vista para activar/desactivar el filtro por palabras clave."""
    # Usaremos la sesión para guardar esta preferencia
    if 'keyword_filter_active' in request.session:
        request.session['keyword_filter_active'] = not request.session['keyword_filter_active']
    else:
        request.session['keyword_filter_active'] = True
    
    status = "activado" if request.session['keyword_filter_active'] else "desactivado"
    messages.success(request, f'Filtro por palabras clave {status} correctamente.')
    
    # Si es una solicitud AJAX, devolver un JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'active': request.session['keyword_filter_active']
        })
    
    return redirect('alertas:alertas_list')


# Vista para listar las configuraciones de alertas por correo del usuario
@login_required
def email_alert_config_list(request):
    configs = EmailAlertConfig.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'alertas/email_alert_configs.html', {'configs': configs})

# Vista para crear una nueva configuración de alerta
@login_required
def email_alert_config_create(request):
    if request.method == 'POST':
        form = EmailAlertConfigForm(request.POST, user=request.user)
        if form.is_valid():
            config = form.save(commit=False)
            config.user = request.user
            config.save()
            form.save_m2m()  # Guardar las relaciones ManyToMany
            messages.success(request, 'Configuración de alerta por correo creada con éxito.')
            return redirect('alertas:email_alert_configs')
    else:
        form = EmailAlertConfigForm(user=request.user)
    
    return render(request, 'alertas/email_alert_config_form.html', {'form': form})

# Vista para editar una configuración existente
@login_required
def email_alert_config_edit(request, pk):
    config = get_object_or_404(EmailAlertConfig, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = EmailAlertConfigForm(request.POST, instance=config, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de alerta actualizada con éxito.')
            return redirect('alertas:email_alert_configs')
    else:
        form = EmailAlertConfigForm(instance=config, user=request.user)
    
    return render(request, 'alertas/email_alert_config_form.html', {'form': form, 'editing': True})

# Vista para eliminar una configuración
@login_required
def email_alert_config_delete(request, pk):
    config = get_object_or_404(EmailAlertConfig, pk=pk, user=request.user)
    
    if request.method == 'POST':
        config.delete()
        messages.success(request, 'Configuración de alerta eliminada con éxito.')
        return redirect('alertas:email_alert_configs')
    
    return render(request, 'alertas/email_alert_config_confirm_delete.html', {'config': config})

# Vista para enviar manualmente una alerta por correo
# Modifica la función send_email_alert en alertas/views.py

@login_required
def send_email_alert(request, pk):
    import logging
    logger = logging.getLogger(__name__)
    
    config = get_object_or_404(EmailAlertConfig, pk=pk, user=request.user)
    
    # Log para verificar que se ha encontrado la configuración
    logger.info(f"Procesando configuración de alerta: {config.name} (ID: {config.pk})")
    
    # Obtener la fecha límite según days_back
    date_limit = timezone.now().date() - datetime.timedelta(days=config.days_back)
    logger.info(f"Buscando alertas desde: {date_limit}")
    
    # Construir la consulta base
    query = Alerta.objects.filter(presentation_date__gte=date_limit)
    
    # Aplicar filtros si están configurados
    if config.source_type:
        query = query.filter(source_type=config.source_type)
        logger.info(f"Filtrando por tipo de fuente: {config.source_type}")
    if config.category:
        query = query.filter(category=config.category)
        logger.info(f"Filtrando por categoría: {config.category}")
    if config.country:
        query = query.filter(country=config.country)
        logger.info(f"Filtrando por país: {config.country}")
    if config.institution:
        query = query.filter(institution=config.institution)
        logger.info(f"Filtrando por institución: {config.institution}")
    
    # Filtrar por palabras clave (si hay alguna configurada)
    keywords = config.keywords.all()
    if keywords.exists():
        from django.db.models import Q
        keyword_filter = Q()
        logger.info(f"Filtrando por palabras clave: {', '.join([k.word for k in keywords])}")
        for keyword in keywords:
            keyword_filter |= Q(title__icontains=keyword.word) | Q(description__icontains=keyword.word)
        query = query.filter(keyword_filter)
    
    # Ordenar por fecha de presentación (más recientes primero)
    alertas = query.order_by('-presentation_date')
    
    logger.info(f"Encontradas {alertas.count()} alertas que coinciden con los criterios")
    
    if alertas.exists():
        # Preparar el contenido del correo
        context = {
            'user': request.user,
            'alertas': alertas,
            'config': config,
        }
        subject = f'Alertas configuradas: {config.name}'
        html_message = render_to_string('alertas/email/alert_email.html', context)
        plain_message = render_to_string('alertas/email/alert_email_plain.html', context)
        
        logger.info(f"Preparando correo para: {config.email}")
        logger.info(f"Asunto: {subject}")
        logger.info(f"Contenido HTML preparado: {len(html_message)} caracteres")
        logger.info(f"Contenido texto plano preparado: {len(plain_message)} caracteres")
        
        # Enviar el correo
        try:
            # Imprimir en la consola para verificación
            print("\n\n================================")
            print(f"ENVIANDO CORREO A: {config.email}")
            print(f"ASUNTO: {subject}")
            print("--------------------------------")
            print("CONTENIDO TEXTO PLANO:")
            print(plain_message)
            print("--------------------------------")
            print("CONTENIDO HTML:")
            print(html_message)
            print("================================\n\n")
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=None,  # Usará DEFAULT_FROM_EMAIL de settings.py
                recipient_list=[config.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Actualizar la fecha del último envío
            config.last_sent = timezone.now()
            config.save()
            
            logger.info(f"Correo enviado exitosamente a {config.email}")
            messages.success(request, f'Alerta enviada con éxito a {config.email}. Se encontraron {alertas.count()} alertas.')
        except Exception as e:
            logger.error(f"Error al enviar correo: {str(e)}")
            messages.error(request, f'Error al enviar la alerta: {str(e)}')
    else:
        logger.info("No se encontraron alertas que coincidan con los criterios")
        messages.info(request, 'No se encontraron alertas que coincidan con los criterios configurados.')
    
    return redirect('alertas:email_alert_configs')

def register_view(request):
    """Vista para el registro de usuarios con email como identificador principal."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Crear el usuario pero no guardarlo aún
            user = form.save(commit=False)
            
            # Asegurarnos que el email sea único
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Este correo electrónico ya está en uso')
                return render(request, 'register.html', {'form': form})
            
            # Generar username a partir del email si no se proporciona
            if not user.username or User.objects.filter(username=user.username).exists():
                base_username = email.split('@')[0]
                username = base_username
                
                # Asegurar que sea único
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user.username = username
            
            # Guardar el usuario
            user.save()
            
            # Autenticar y loguear al usuario
            login(request, user)
            messages.success(request, f"¡Bienvenido, {user.first_name}! Tu cuenta ha sido creada con éxito.")
            
            # Redirigir al usuario a la página principal
            return redirect('alertas:alertas_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


class CustomLoginView(LoginView):
    """Vista de inicio de sesión personalizada que usa el formulario con soporte para email"""
    form_class = CustomAuthenticationForm
    template_name = 'login.html'
    
    def get_success_url(self):
        return reverse_lazy('alertas:alertas_list')

# nueva vista que devuelva las instituciones para un país específico
@login_required
def get_institutions_by_country(request):
    """Vista AJAX para obtener las instituciones de un país específico."""
    country = request.GET.get('country')
    
    # Construir la consulta
    query = Alerta.objects.values_list('institution', flat=True).distinct().order_by('institution')
    
    # Si se proporciona un país, filtrar por ese país
    if country:
        query = query.filter(country=country)
    
    # Formar el array para el select
    institution_choices = [('', 'Todas')]
    institution_choices.extend([(inst, inst) for inst in query if inst])
    
    return JsonResponse({'institutions': institution_choices})