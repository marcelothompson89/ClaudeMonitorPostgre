import asyncio
import importlib
import logging
import time
from datetime import datetime
from typing import Dict, Any, Callable, List
from .models import ScraperLog


from alertas.models import Alerta

logger = logging.getLogger(__name__)

# Registro de scrapers disponibles
AVAILABLE_SCRAPERS = {
    'argentina_noti_anmat': {
        'module': 'scrapers.scrapers.anmat_noti_ar',
        'function': 'scrape_anmat_noti_ar',
        'name': 'ANMAT Noticias de Argentina',
        'description': 'Obtiene noticias de ANMAT Argentina'
    },
    'mexico_animalpolitico': {
        'module': 'scrapers.scrapers.animalpolitico_mx',
        'function': 'scrape_animal_politico_salud',
        'name': 'Animal Político México',
        'description': 'Obtiene noticias del diario Animal Político México'
    },
    'chile_anamed': {
        'module': 'scrapers.scrapers.anamed_cl',
        'function': 'scrape_anamed_cl',
        'name': 'ANAMED Chile',
        'description': 'Obtiene alertas de ANAMED Chile'
    },
    'brasil_anvisa_normas': {
        'module': 'scrapers.scrapers.anvisa_normas_br',
        'function': 'scrape_anvisa_normas_br',
        'name': 'ANVISA Normas de Brasil',
        'description': 'Obtiene normas de ANVISA Brasil'
    },
    'brasil_anvisa_noticias': {
        'module': 'scrapers.scrapers.anvisa_noti_br',
        'function': 'scrape_anvisa_noti_br',
        'name': 'ANVISA Noticias de Brasil',
        'description': 'Obtiene noticias de ANVISA Brasil'
    },
    'argentina_boletinoficial': {
        'module': 'scrapers.scrapers.boletinoficial_ar',
        'function': 'scrape_boletin_oficial_ar',
        'name': 'Boletín Oficial de Argentina',
        'description': 'Obtiene avises de Boletín Oficial de Argentina'
    },
    'cepal_reg': {
        'module': 'scrapers.scrapers.cepal_reg',
        'function': 'scrape_cepal_noticias_reg',
        'name': 'CEPAL Regional',
        'description': 'Obtiene noticias de CEPAL Regional'
    },
    'mexico_cofepris_noticias': {
        'module': 'scrapers.scrapers.cofepris_noti_mx',
        'function': 'scrape_cofepris_noti_mx',
        'name': 'COFEPRIS Noticias de México',
        'description': 'Obtiene noticias de COFEPRIS México'
    },
    'peru_congreso_comunicaciones': {
        'module': 'scrapers.scrapers.congreso_comu_pe',
        'function': 'scrape_congreso_comu_pe',
        'name': 'Comunicaciones Congreso de Perú',
        'description': 'Obtiene Comunicaciones  del Congreso de Perú'
    },
    'colombia_congreso_legislativo_proyectos': {
        'module': 'scrapers.scrapers.congreso_legislativo_co',
        'function': 'scrape_camara_proyectos_co',
        'name': 'Congreso Legislativo de Colombia',
        'description': 'Obtiene proyectos de ley del Congreso Legislativo de Colombia'
    },
    'brasil_congreso_normas': {
        'module': 'scrapers.scrapers.congreso_normas_br',
        'function': 'scrape_congreso_normas_br',
        'name': 'Congreso de Brasil',
        'description': 'Obtiene normas legales del Congreso de Brasil'
    },
    'peru_congreso_proyectos': {
        'module': 'scrapers.scrapers.congreso_proyectos_pe',
        'function': 'scrape_congreso_proyectos_pe',
        'name': 'Congreso de Perú',
        'description': 'Obtiene proyectos de ley del Congreso de Perú'
    },
    'peru_digemid_noticias': {
        'module': 'scrapers.scrapers.digemid_pe',
        'function': 'scrape_digemid_noticias',
        'name': 'DIGEMID Noticias de Perú',
        'description': 'Obtiene noticias de DIGEMID Perú'
    },
    'peru_digesa_comunicaciones': {
        'module': 'scrapers.scrapers.digesa_comu_pe',
        'function': 'scrape_digesa_comunicaciones_pe',
        'name': 'DIGESA Comunicaciones de Perú',
        'description': 'Obtiene comunicaciones de DIGESA Perú'
    },
    'peru_digesa_noticias': {
        'module': 'scrapers.scrapers.digesa_noti_pe',
        'function': 'scrape_digesa_noticias_pe',
        'name': 'DIGESA Noticias de Perú',
        'description': 'Obtiene noticias de DIGESA Perú'
    },
    'brasil_diputados_noticias': {
        'module': 'scrapers.scrapers.diputados_noti_br',
        'function': 'scrape_diputados_noti_br',
        'name': 'Diputados de Brasil',
        'description': 'Obtiene noticias de Diputados de Brasil'
    },
    'chile_diputados_noticias': {
        'module': 'scrapers.scrapers.diputados_noti_cl',
        'function': 'scrape_diputados_noti_cl',
        'name': 'Noticias Diputados de Chile',
        'description': 'Obtiene noticias de Diputados de Chile'
    },
    'chile_diputados_proyectos': {
        'module': 'scrapers.scrapers.diputados_proyectos_cl',
        'function': 'scrape_diputados_proyectos_cl',
        'name': 'Proyectos de Ley Diputados de Chile',
        'description': 'Obtiene proyectos de ley de Diputados de Chile'
    },
    'brasil_dou': {
        'module': 'scrapers.scrapers.dou_br',
        'function': 'scrape_dou_br',
        'name': 'Diário Oficial da União',
        'description': 'Obtiene avises de Diário Oficial da União'
    },
    'mexico_el_universal_salud': {
        'module': 'scrapers.scrapers.eluniversal_mx',
        'function': 'scrape_el_universal_salud_mx',
        'name': 'El Universal Salud México',
        'description': 'Obtiene noticias de El Universal Salud'
    },
    'panama_farmaydrogas': {
        'module': 'scrapers.scrapers.farmaydrogas_pa',
        'function': 'scrape_farmaydrogas_pa',
        'name': 'Farmaydrogas Panamá',
        'description': 'Obtiene noticias de Farmaydrogas Panamá'
    },
    'argentina_hcdn': {
        'module': 'scrapers.scrapers.hcdn_ar',
        'function': 'scrape_hcdn_ar',
        'name': 'Cámara de Diputados de Argentina',
        'description': 'Obtiene noticias de HCDN Argentina'
    },
    'colombia_invimia_noticias': {
        'module': 'scrapers.scrapers.invimia_noti_co',
        'function': 'scrape_invima_noticias_co',
        'name': 'INVIMA Noticias de Colombia',
        'description': 'Obtiene noticias de INVIMA Colombia'
    },
    'chile_ispch_noticias': {
        'module': 'scrapers.scrapers.ispch_noticias_cl',
        'function': 'scrape_ispch_noticias_cl',
        'name': 'ISPCH Noticias de Chile',
        'description': 'Obtiene noticias de ISPCH Chile'
    },
    'chile_ispch_resoluciones': {
        'module': 'scrapers.scrapers.ispch_resoluciones_cl',
        'function': 'scrape_ispch_resoluciones_cl',
        'name': 'ISPCH Resoluciones de Chile',
        'description': 'Obtiene resoluciones de ISPCH Chile'
    },
    'latam_regnews': {
        'module': 'scrapers.scrapers.latam_regnews_reg',
        'function': 'scrape_latam_regnews',
        'name': 'Latam ReguNews',
        'description': 'Obtiene noticias de Latam ReguNews'
    },
    'peru_minsa_normas': {
        'module': 'scrapers.scrapers.minsa_normas_pe',
        'function': 'scrape_minsa_normas_pe',
        'name': 'MINSA Normas de Perú',
        'description': 'Obtiene normas legales de MINSA Perú'
    },
    'peru_minsa_noticias': {
        'module': 'scrapers.scrapers.minsa_noticias_pe',
        'function': 'scrape_minsa_noticias_pe',
        'name': 'MINSA Noticias de Perú',
        'description': 'Obtiene noticias de MINSA Perú'
    },
    'mexico_min_salud_comu': {
        'module': 'scrapers.scrapers.minsalud_comu_mx',
        'function': 'scrape_minsalud_comu_mx',
        'name': 'MinSalud Comunicación de México',
        'description': 'Obtiene comunicaciones de MinSalud México'
    },
    'colombia_min_salud_decre': {
        'module': 'scrapers.scrapers.minsalud_decre_co',
        'function': 'scrape_minsalud_decre_co',
        'name': 'MinSalud Decretos de Colombia',
        'description': 'Obtiene decretos de MinSalud Colombia'
    },
    'panama_min_salud_med': {
        'module': 'scrapers.scrapers.minsalud_med_pa',
        'function': 'scrape_minsa_med_pa',
        'name': 'MinSalud Medicamentos de Panamá',
        'description': 'Obtiene medicamentos de MinSalud Panamá'
    },
    'argentina_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_ar',
        'function': 'scrape_minsalud_noti_ar',
        'name': 'MinSalud Noticias de Argentina',
        'description': 'Obtiene noticias de MinSalud Argentina'
    },
    'brasil_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_br',
        'function': 'scrape_minsalud_noticias_br',
        'name': 'MinSalud Noticias de Brasil',
        'description': 'Obtiene noticias de MinSalud Brasil'
    },
    'colombia_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_co',
        'function': 'scrape_minsalud_noticias_co',
        'name': 'MinSalud Noticias de Colombia',
        'description': 'Obtiene noticias de MinSalud Colombia'
    },
    'costa_rica_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_cr',
        'function': 'scrape_ministerio_salud_cr',
        'name': 'MinSalud Noticias de Costa Rica',
        'description': 'Obtiene noticias de MinSalud Costa Rica'
    },
    'republica_dominicana_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_do',
        'function': 'scrape_minsalud_noti_do',
        'name': 'MinSalud Noticias de República Dominicana',
        'description': 'Obtiene noticias de MinSalud República Dominicana'
    },
    'guatemala_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_gt',
        'function': 'scrape_minsalud_noti_gt',
        'name': 'MinSalud Noticias de Guatemala',
        'description': 'Obtiene noticias de MinSalud Guatemala'
    },
    'mexico_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_mx',
        'function': 'scrape_minsalud_noti_mx',
        'name': 'MinSalud Noticias de México',
        'description': 'Obtiene noticias de MinSalud México'
    },
    'panama_min_salud_noti': {
        'module': 'scrapers.scrapers.minsalud_noti_pa',
        'function': 'scrape_minsa_noti_pa',
        'name': 'MinSalud Noticias de Panamá',
        'description': 'Obtiene noticias de MinSalud Panamá'
    },
    'colombia_min_salud_resol': {
        'module': 'scrapers.scrapers.minsalud_resol_co',
        'function': 'scrape_minsalud_resoluciones_co',
        'name': 'MinSalud Resoluciones de Colombia',
        'description': 'Obtiene resoluciones de MinSalud Colombia'
    },
    'paho_noti': {
        'module': 'scrapers.scrapers.paho_noti_reg',
        'function': 'scrape_paho_noti_reg',
        'name': 'PAHO Noticias',
        'description': 'Obtiene noticias de PAHO'
    },
    'parlatino': {
        'module': 'scrapers.scrapers.parlatino_reg',
        'function': 'scrape_parlatino_reg',
        'name': 'Parlatino',
        'description': 'Obtiene noticias de Parlatino'
    },
    'proceso_mx': {
        'module': 'scrapers.scrapers.periodico_proceso_mx',
        'function': 'scrape_proceso_mx',
        'name': 'Proceso',
        'description': 'Obtiene noticias de Proceso'
    },
    'senado_noti_ar': {
        'module': 'scrapers.scrapers.senado_noti_ar',
        'function': 'scrape_senado_noti_ar',
        'name': 'Senado Noticias de Argentina',
        'description': 'Obtiene noticias de Senado de Argentina'
    },
    'senado_noti_br': {
        'module': 'scrapers.scrapers.senado_noti_br',
        'function': 'scrape_senado_noticias_br',
        'name': 'Senado Noticias de Brasil',
        'description': 'Obtiene noticias de Senado de Brasil'
    },
    'senado_noti_cl': {
        'module': 'scrapers.scrapers.senado_noticias_cl',
        'function': 'scrape_senado_noticias_cl',
        'name': 'Senado Noticias de Chile',
        'description': 'Obtiene noticias de Senado de Chile'
    },
    'sica_noti_cam': {
        'module': 'scrapers.scrapers.sica_noti_cam',
        'function': 'scrape_sica_noticias_cam',
        'name': 'SICA Noticias de Centroamérica',
        'description': 'Obtiene noticias de SICA de Centroamérica'
    },
    'wto_eping_glo': {
        'module': 'scrapers.scrapers.wto_eping_glo',
        'function': 'scrape_eping_glo',
        'name': 'WTO Eping Global',
        'description': 'Obtiene noticias de WTO Eping Global'
    },
    'argentina_anmat': {
        'module': 'scrapers.scrapers.anmat_alertas_ar',
        'function': 'scrape_anmat_alertas_ar',
        'name': 'ANMAT Argentina Alertas',
        'description': 'Obtiene alertas de ANMAT Argentina'
    },
    'senasica_noti_mx': {
        'module': 'scrapers.scrapers.senasica_noti_mx',
        'function': 'scrape_senasica_noti_mx',
        'name': 'SENASICA Noticias de México',
        'description': 'Obtiene noticias de SENASICA de México'
    },
    'cofepris_docu_mx': {
        'module': 'scrapers.scrapers.cofepris_docu_mx',
        'function': 'scrape_cofepris_docu_mx',
        'name': 'Cofepris Documentos de México',
        'description': 'Obtiene documentos de Cofepris de México'
    },
    
    # Añade más scrapers aquí usando el mismo formato
    # 'otro_scraper': {
    #     'module': 'scrapers.scrapers.otro_scraper',
    #     'function': 'scrape_otro_site',
    #     'name': 'Nombre descriptivo',
    #     'description': 'Descripción del scraper'
    # },
}

def save_items_to_db(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Guarda los items del scraper en la base de datos.
    
    Args:
        items: Lista de diccionarios con los datos extraídos
        
    Returns:
        Dict con estadísticas sobre la operación
    """
    created_count = 0
    updated_count = 0
    error_count = 0
    error_details = []
    
    for item in items:
        try:
            # Crear o actualizar la Alerta
            defaults = {
                'title': item['title'],
                'description': item['description'],
                'source_type': item['source_type'],
                'category': item['category'],
                'country': item['country'],
                'institution': item['institution'],
                'presentation_date': item['presentation_date']
            }
            
            # Manejo de los campos de metadatos
            if 'metadata' in item and item['metadata']:
                if 'image_url' in item['metadata']:
                    defaults['metadata_nota_url'] = item['metadata'].get('image_url')
            
            # Buscar por source_url, title y presentation_date según la restricción unique
            obj_created = False  # Valor predeterminado en caso de error
            
            if item.get('source_url') and item.get('presentation_date'):
                alerta, obj_created = Alerta.objects.update_or_create(
                    source_url=item['source_url'],
                    title=item['title'],
                    presentation_date=item['presentation_date'],
                    defaults=defaults
                )
            elif item.get('presentation_date'):  # Si no hay source_url pero sí fecha
                alerta, obj_created = Alerta.objects.update_or_create(
                    title=item['title'],
                    presentation_date=item['presentation_date'],
                    defaults=defaults
                )
            else:  # Si no hay ni source_url ni fecha, usar solo el título
                alerta, obj_created = Alerta.objects.update_or_create(
                    title=item['title'],
                    defaults=defaults
                )
                
            if obj_created:
                created_count += 1
            else:
                updated_count += 1
                
        except Exception as e:
            error_count += 1
            error_msg = f"Error al guardar alerta {item.get('title', 'Sin título')}: {str(e)}"
            logger.error(error_msg)
            error_details.append(error_msg)
    
    return {
        'created': created_count,
        'updated': updated_count,
        'errors': error_count,
        'error_details': '\n'.join(error_details),
        'items_processed': len(items)
    }

def run_scraper(scraper_id: str) -> Dict[str, Any]:
    """
    Ejecuta un scraper específico por su ID y guarda los resultados en la base de datos.
    """
    start_time = time.time()
    
    if scraper_id not in AVAILABLE_SCRAPERS:
        result = {
            'success': False,
            'message': f"Scraper con ID '{scraper_id}' no encontrado"
        }
        save_scraper_log(scraper_id, result, 0)
        return result
    
    scraper_info = AVAILABLE_SCRAPERS[scraper_id]
    
    try:
        # Importar dinámicamente el módulo y función del scraper
        module = importlib.import_module(scraper_info['module'])
        scraper_function = getattr(module, scraper_info['function'])
        
        # Ejecutar el scraper
        items = asyncio.run(scraper_function())
        
        # Guardar los resultados en la base de datos
        stats = save_items_to_db(items)
        
        result = {
            'success': True,
            'scraper_id': scraper_id,
            'scraper_name': scraper_info['name'],
            'items_processed': stats['items_processed'],
            'created': stats['created'],
            'updated': stats['updated'],
            'errors': stats['errors'],
            'error_details': stats.get('error_details', ''),
            'message': f"Scraper ejecutado con éxito. Procesados {stats['items_processed']} items."
        }
        
        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        
        # Guardar log
        save_scraper_log(scraper_id, result, execution_time)
        
        return result
    
    except Exception as e:
        error_msg = f"Error ejecutando scraper '{scraper_id}': {str(e)}"
        logger.error(error_msg)
        result = {
            'success': False,
            'scraper_id': scraper_id,
            'scraper_name': scraper_info['name'],
            'message': error_msg,
            'error_details': str(e)
        }
        
        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        
        # Guardar log
        save_scraper_log(scraper_id, result, execution_time)
        
        return result

def run_all_scrapers() -> Dict[str, Any]:
    """
    Ejecuta todos los scrapers disponibles.
    """
    start_time = time.time()
    
    results = {
        'timestamp': datetime.now(),
        'scrapers': {}
    }
    
    # Estadísticas globales
    total_processed = 0
    total_created = 0
    total_updated = 0
    total_errors = 0
    failures = 0
    
    for scraper_id in AVAILABLE_SCRAPERS:
        result = run_scraper(scraper_id)
        results['scrapers'][scraper_id] = result
        
        if result['success']:
            total_processed += result.get('items_processed', 0)
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            total_errors += result.get('errors', 0)
        else:
            failures += 1
    
    execution_time = time.time() - start_time
    
    results['summary'] = {
        'total_processed': total_processed,
        'total_created': total_created,
        'total_updated': total_updated,
        'total_errors': total_errors,
        'failures': failures,
        'success': failures == 0,
        'execution_time': execution_time
    }
    
    # Registrar la ejecución completa de todos los scrapers
    try:
        log = ScraperLog(
            scraper_id='all_scrapers',
            scraper_name='Todos los scrapers',
            items_processed=total_processed,
            items_created=total_created,
            items_updated=total_updated,
            items_failed=total_errors,
            success=failures == 0,
            message=f"Ejecutados {len(AVAILABLE_SCRAPERS)} scrapers. {failures} fallaron.",
            execution_time=execution_time
        )
        log.save()
    except Exception as e:
        logger.error(f"Error al guardar log de ejecución completa: {str(e)}")
    
    return results

def get_available_scrapers():
    """
    Devuelve la lista de scrapers disponibles con su información.
    
    Returns:
        List de diccionarios con información de cada scraper
    """
    return [
        {
            'id': scraper_id,
            'name': info['name'],
            'description': info['description']
        }
        for scraper_id, info in AVAILABLE_SCRAPERS.items()
    ]

def save_scraper_log(scraper_id, result, execution_time=None):
    """
    Guarda un registro de la ejecución del scraper en la base de datos.
    
    Args:
        scraper_id: Identificador del scraper
        result: Diccionario con los resultados de la ejecución
        execution_time: Tiempo de ejecución en segundos (opcional)
    """
    try:
        log = ScraperLog(
            scraper_id=scraper_id,
            scraper_name=result.get('scraper_name', 'Desconocido'),
            items_processed=result.get('items_processed', 0),
            items_created=result.get('created', 0),
            items_updated=result.get('updated', 0),
            items_failed=result.get('errors', 0),
            success=result.get('success', False),
            message=result.get('message', ''),
            error_details=result.get('error_details', ''),
            execution_time=execution_time
        )
        log.save()
        return log
    except Exception as e:
        logger.error(f"Error al guardar log del scraper {scraper_id}: {str(e)}")
        return None