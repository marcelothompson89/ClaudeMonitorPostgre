# alertas/utils.py
import re
import dateparser
from datetime import datetime, timedelta
from django.utils import timezone


# Palabras clave que indican que una alerta podría ser un evento
EVENT_KEYWORDS = [
    'congreso', 'conferencia', 'seminario', 'webinar', 'taller',
    'workshop', 'foro', 'reunión', 'sesión', 'simposio', 'jornada',
    'encuentro', 'convocatoria', 'inscripción', 'registro', 'evento',
    'charla', 'curso', 'capacitación', 'training', 'cumbre', 'summit',
    'mesa redonda', 'panel', 'debate', 'expo', 'feria', 'exhibición',
    'lanzamiento', 'presentación', 'inauguración', 'ceremonia',
    'asamblea', 'cita', 'audiencia', 'consulta pública'
]


def contains_event_keywords(text):
    """
    Verifica si el texto contiene palabras clave de eventos.

    Args:
        text (str): Texto a analizar (título + descripción)

    Returns:
        bool: True si contiene palabras clave de evento
    """
    if not text:
        return False

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in EVENT_KEYWORDS)


def extract_dates_from_text(text):
    """
    Extrae fechas del texto en español.

    Args:
        text (str): Texto del que extraer fechas

    Returns:
        dict: {'start_date': date or None, 'end_date': date or None}
    """
    if not text:
        return {'start_date': None, 'end_date': None}

    # Configuración para español
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': timezone.now(),
        'RETURN_AS_TIMEZONE_AWARE': True,
        'TIMEZONE': 'America/Santiago',  # Puedes ajustar según tu zona
    }

    # Patrones comunes para rangos de fechas en español
    date_range_patterns = [
        r'del?\s+(\d{1,2})\s+al?\s+(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})',
        r'desde\s+el?\s+(\d{1,2})\s+de\s+(\w+)\s+hasta\s+el?\s+(\d{1,2})\s+de\s+(\w+)',
        r'(\d{1,2})\s*-\s*(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})',
    ]

    start_date = None
    end_date = None

    # Intentar detectar rangos de fechas
    for pattern in date_range_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Extraer y parsear las fechas del rango
            try:
                groups = match.groups()
                if len(groups) == 4:
                    if '-' in pattern or 'al' in pattern:
                        # Patrón tipo "del 15 al 20 de marzo de 2026"
                        start_str = f"{groups[0]} de {groups[2]} de {groups[3]}"
                        end_str = f"{groups[1]} de {groups[2]} de {groups[3]}"
                    else:
                        # Patrón tipo "desde el 15 de marzo hasta el 20 de abril"
                        start_str = f"{groups[0]} de {groups[1]}"
                        end_str = f"{groups[2]} de {groups[3]}"

                    start_date = dateparser.parse(start_str, settings=settings)
                    end_date = dateparser.parse(end_str, settings=settings)

                    if start_date and end_date:
                        return {
                            'start_date': start_date.date(),
                            'end_date': end_date.date()
                        }
            except:
                pass

    # Si no se encontró un rango, buscar fechas individuales
    # Dividir el texto en fragmentos más pequeños para buscar fechas
    sentences = re.split(r'[.!?;\n]', text)

    for sentence in sentences[:5]:  # Revisar las primeras 5 oraciones
        parsed_date = dateparser.parse(
            sentence,
            languages=['es'],
            settings=settings
        )

        if parsed_date:
            # Validar que la fecha esté en un rango razonable (próximos 2 años)
            max_date = timezone.now() + timedelta(days=730)
            if timezone.now() <= parsed_date <= max_date:
                if not start_date:
                    start_date = parsed_date.date()
                    break

    return {
        'start_date': start_date,
        'end_date': end_date
    }


def suggest_event_type(title, description):
    """
    Sugiere el tipo de evento basado en palabras clave.

    Args:
        title (str): Título de la alerta
        description (str): Descripción de la alerta

    Returns:
        str: Tipo de evento sugerido ('evento', 'conferencia', 'comite', etc.)
    """
    text = f"{title} {description}".lower()

    # Mapeo de palabras clave a tipos de evento
    type_keywords = {
        'conferencia': ['conferencia', 'congress', 'congreso'],
        'comite': ['comité', 'comite', 'reunión de comité', 'sesión de comité'],
        'politico': ['consulta pública', 'audiencia', 'normativa', 'regulación'],
        'feriado': ['feriado', 'festivo', 'asueto'],
    }

    for event_type, keywords in type_keywords.items():
        if any(keyword in text for keyword in keywords):
            return event_type

    return 'evento'  # Por defecto
