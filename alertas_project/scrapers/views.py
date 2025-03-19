from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .tasks import run_scraper, run_all_scrapers, get_available_scrapers

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