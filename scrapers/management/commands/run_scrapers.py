import json
from django.core.management.base import BaseCommand, CommandError
from scrapers.tasks import run_scraper, run_all_scrapers, get_available_scrapers

class Command(BaseCommand):
    help = 'Ejecuta los scrapers disponibles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scraper',
            type=str,
            help='ID específico del scraper a ejecutar. Si no se especifica, se ejecutan todos.'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Muestra la lista de scrapers disponibles'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Devuelve los resultados en formato JSON'
        )

    def handle(self, *args, **options):
        list_scrapers = options.get('list')
        scraper_id = options.get('scraper')
        json_output = options.get('json')
        
        # Mostrar lista de scrapers disponibles
        if list_scrapers:
            scrapers = get_available_scrapers()
            if json_output:
                self.stdout.write(json.dumps(scrapers, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("Scrapers disponibles:"))
                for scraper in scrapers:
                    self.stdout.write(f"- {scraper['id']}: {scraper['name']} - {scraper['description']}")
            return
        
        try:
            if scraper_id:
                # Ejecutar un scraper específico
                result = run_scraper(scraper_id)
                
                if json_output:
                    self.stdout.write(json.dumps(result, default=str, indent=2))
                else:
                    if result['success']:
                        self.stdout.write(self.style.SUCCESS(
                            f"Scraper '{result['scraper_name']}' ejecutado con éxito. "
                            f"Procesados {result.get('items_processed', 0)} items "
                            f"({result.get('created', 0)} nuevos, {result.get('updated', 0)} actualizados)"
                        ))
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"Error al ejecutar el scraper '{result.get('scraper_name')}': {result.get('message')}"
                        ))
            else:
                # Ejecutar todos los scrapers
                results = run_all_scrapers()
                
                if json_output:
                    self.stdout.write(json.dumps(results, default=str, indent=2))
                else:
                    summary = results['summary']
                    if summary['success']:
                        self.stdout.write(self.style.SUCCESS(
                            f"Todos los scrapers ejecutados con éxito. "
                            f"Procesados {summary['total_processed']} items "
                            f"({summary['total_created']} nuevos, {summary['total_updated']} actualizados)"
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Algunos scrapers fallaron. {summary['failures']} de {len(results['scrapers'])} fallaron. "
                            f"Procesados {summary['total_processed']} items."
                        ))
                        
                    # Mostrar detalles de cada scraper
                    self.stdout.write("\nDetalles por scraper:")
                    for scraper_id, result in results['scrapers'].items():
                        status = "✅ Éxito" if result['success'] else "❌ Error"
                        self.stdout.write(f"- {result.get('scraper_name', scraper_id)}: {status}")
                        if result['success']:
                            self.stdout.write(f"  Items procesados: {result.get('items_processed', 0)}")
                            self.stdout.write(f"  Nuevos: {result.get('created', 0)}, Actualizados: {result.get('updated', 0)}")
                        else:
                            self.stdout.write(f"  Error: {result.get('message')}")
        
        except Exception as e:
            raise CommandError(f"Error al ejecutar los scrapers: {str(e)}")