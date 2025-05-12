# alertas/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .models import Alerta
from django.db.models import Q
import logging

logger = logging.getLogger('alertas')

def send_alert_email(config, user):
    """Envía un email con las alertas según la configuración"""
    
    # Calcular el rango de fechas según days_back
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=config.days_back)
    
    # Construir la consulta base
    query = Q(presentation_date__gte=start_date, presentation_date__lte=end_date)
    
    # Aplicar filtros según la configuración
    if config.source_type:
        query &= Q(source_type=config.source_type)
    
    if config.category:
        query &= Q(category=config.category)
    
    if config.country:
        query &= Q(country=config.country)
    
    if config.institution:
        query &= Q(institution=config.institution)
    
    # Obtener las alertas
    alertas = Alerta.objects.filter(query)
    
    # Filtrar por palabras clave si están configuradas
    if config.keywords.exists():
        keywords = config.keywords.filter(active=True).values_list('word', flat=True)
        if keywords:
            keyword_query = Q()
            for keyword in keywords:
                keyword_query |= Q(title__icontains=keyword) | Q(description__icontains=keyword)
            alertas = alertas.filter(keyword_query)
    
    # Ordenar por fecha de presentación
    alertas = alertas.order_by('-presentation_date')
    
    if not alertas:
        logger.info(f"No se encontraron alertas para la configuración {config.name}")
        return False
    
    # Preparar el contexto para el email
    context = {
        'config': config,
        'user': user,
        'alertas': alertas,
        'count': alertas.count(),
    }
    
    # Renderizar el email
    html_message = render_to_string('alertas/email/alert_email.html', context)
    plain_message = render_to_string('alertas/email/alert_email_plain.html', context)
    
    # Enviar el email
    subject = f'Alertas: {config.name} - {timezone.now().strftime("%d/%m/%Y")}'
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=None,  # Usa DEFAULT_FROM_EMAIL
            recipient_list=[config.email],
            html_message=html_message,
        )
        
        logger.info(f"Email enviado exitosamente a {config.email} con {alertas.count()} alertas")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {config.email}: {str(e)}")
        return False