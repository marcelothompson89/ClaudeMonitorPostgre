# alertas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
import json
import datetime

from .models import Alerta, User, Keyword
from .forms import AlertaFilterForm, KeywordForm

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
    
    # Paginación
    page_size = int(request.GET.get('page_size', 50))
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