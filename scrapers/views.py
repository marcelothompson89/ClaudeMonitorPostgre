from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import ScraperLog
import hmac
import hashlib
import logging

from .tasks import run_scraper, run_all_scrapers, get_available_scrapers


logger = logging.getLogger(__name__)

@staff_member_required
def scrapers_dashboard(request):
    """Vista para mostrar el panel de scrapers."""
    scrapers = get_available_scrapers()
    
    # Añadir URL para ejecutar cada scraper
    for scraper in scrapers:
        scraper['run_url'] = reverse('scrapers:run_specific', args=[scraper['id']])
    
    context = {
        'scrapers': scrapers,
        'run_all_url': reverse('scrapers:run_all')
    }
    
    return render(request, 'scrapers/dashboard.html', context)

@staff_member_required
@require_POST
def run_scrapers_manually(request):
    """Vista para ejecutar todos los scrapers manualmente."""
    results = run_all_scrapers()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(results)
    
    # Si no es AJAX, redirigir con mensaje
    if results['summary']['success']:
        messages.success(
            request, 
            f"Todos los scrapers ejecutados con éxito. Procesados {results['summary']['total_processed']} items " 
            f"({results['summary']['total_created']} nuevos, {results['summary']['total_updated']} actualizados)"
        )
    else:
        messages.error(
            request, 
            f"Hubo errores al ejecutar algunos scrapers. {results['summary']['failures']} fallaron."
        )
    
    return redirect(reverse('scrapers:dashboard'))

@staff_member_required
@require_POST
def run_specific_scraper(request, scraper_id):
    """Vista para ejecutar un scraper específico."""
    result = run_scraper(scraper_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(result)
    
    # Si no es AJAX, redirigir con mensaje
    if result['success']:
        messages.success(
            request, 
            f"Scraper '{result['scraper_name']}' ejecutado con éxito. Procesados {result.get('items_processed', 0)} items " 
            f"({result.get('created', 0)} nuevos, {result.get('updated', 0)} actualizados)"
        )
    else:
        messages.error(request, f"Error al ejecutar el scraper '{result.get('scraper_name')}': {result.get('message')}")
    
    return redirect(reverse('scrapers:dashboard'))

@staff_member_required
def view_scraper_logs(request):
    """Vista para consultar los logs de ejecución de scrapers."""
    logs = ScraperLog.objects.all()
    
    # Filtros por scraper_id
    scraper_id = request.GET.get('scraper_id')
    if scraper_id:
        logs = logs.filter(scraper_id=scraper_id)
    
    # Filtro por éxito/error
    status = request.GET.get('status')
    if status == 'success':
        logs = logs.filter(success=True)
    elif status == 'error':
        logs = logs.filter(success=False)
    
    # Filtro por fecha
    date_range = request.GET.get('date_range')
    if date_range == 'today':
        today = timezone.now().date()
        logs = logs.filter(timestamp__date=today)
    elif date_range == 'yesterday':
        yesterday = timezone.now().date() - timedelta(days=1)
        logs = logs.filter(timestamp__date=yesterday)
    elif date_range == 'last_7_days':
        last_week = timezone.now() - timedelta(days=7)
        logs = logs.filter(timestamp__gte=last_week)
    elif date_range == 'last_30_days':
        last_month = timezone.now() - timedelta(days=30)
        logs = logs.filter(timestamp__gte=last_month)
    
    # Paginación
    paginator = Paginator(logs, 25)  # 25 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para el filtro de scraper_id
    available_scrapers = [{'id': 'all_scrapers', 'name': 'Todos los scrapers'}]
    available_scrapers.extend(get_available_scrapers())
    
    context = {
        'page_obj': page_obj,
        'available_scrapers': available_scrapers
    }
    
    return render(request, 'scrapers/logs.html', context)

@staff_member_required
def view_scraper_log_detail(request, log_id):
    """Vista para ver el detalle de un log específico."""
    try:
        log = ScraperLog.objects.get(id=log_id)
    except ScraperLog.DoesNotExist:
        messages.error(request, "El registro de log no existe.")
        return redirect('scrapers:logs')
    
    context = {
        'log': log
    }
    
    return render(request, 'scrapers/log_detail.html', context)


@csrf_exempt
@require_POST
def run_scrapers_api(request):
    """
    Endpoint para iniciar la ejecución de scrapers desde GitHub Actions
    """
    # Verificar el token de seguridad
    api_key = request.headers.get('X-API-Key', '')
    expected_key = getattr(settings, 'SCRAPER_API_TOKEN', '')
    
    if not expected_key:
        logger.error("SCRAPER_API_TOKEN no configurado en settings")
        return JsonResponse({
            'status': 'error',
            'message': 'Error de configuración del servidor'
        }, status=500)
    
    if not hmac.compare_digest(api_key, expected_key):
        logger.warning("Intento de acceso con token inválido")
        return JsonResponse({
            'status': 'error',
            'message': 'No autorizado'
        }, status=403)
    
    try:
        logger.info("Iniciando ejecución de scrapers vía API")
        results = run_all_scrapers()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Scrapers ejecutados correctamente',
            'summary': results['summary']
        })
        
    except Exception as e:
        logger.exception("Error al ejecutar scrapers")
        return JsonResponse({
            'status': 'error',
            'message': f'Error al ejecutar scrapers: {str(e)}'
        }, status=500)