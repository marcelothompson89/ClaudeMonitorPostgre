# migration.py
import os
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alertas_project.settings')
django.setup()

# Ahora puedes importar tus modelos
from alertas.models import Keyword, Source, Alerta
from django.contrib.auth.models import User
from django.db import connections

def migrate_data():
    print("Iniciando migración de datos...")
    
    # Asegúrate de que ambas bases de datos estén definidas en settings.py
    # 'default' debe ser PostgreSQL y 'old_db' debe ser tu base de datos anterior
    
    # Migrar Keywords
    keywords = Keyword.objects.using('old_db').all()
    print(f"Migrando {keywords.count()} keywords...")
    for kw in keywords:
        try:
            # Asumiendo que ya tienes los mismos usuarios en la nueva base de datos
            user = User.objects.get(username=kw.user.username)
            Keyword.objects.using('default').get_or_create(
                word=kw.word,
                user=user,
                defaults={
                    'created_at': kw.created_at,
                    'active': kw.active
                }
            )
        except Exception as e:
            print(f"Error migrando keyword {kw.word}: {str(e)}")
    
    # Migrar Sources
    sources = Source.objects.using('old_db').all()
    print(f"Migrando {sources.count()} sources...")
    for source in sources:
        try:
            Source.objects.using('default').get_or_create(
                name=source.name,
                url=source.url,
                defaults={
                    'scraper_type': source.scraper_type,
                    'active': source.active,
                    'created_at': source.created_at,
                    'last_scraped': source.last_scraped
                }
            )
        except Exception as e:
            print(f"Error migrando source {source.name}: {str(e)}")
    
    # Migrar Alertas
    alertas = Alerta.objects.using('old_db').all()
    print(f"Migrando {alertas.count()} alertas...")
    for alerta in alertas:
        try:
            Alerta.objects.using('default').get_or_create(
                title=alerta.title,
                presentation_date=alerta.presentation_date,
                defaults={
                    'description': alerta.description,
                    'source_type': alerta.source_type,
                    'category': alerta.category,
                    'country': alerta.country,
                    'source_url': alerta.source_url,
                    'institution': alerta.institution,
                    'metadata_nota_url': alerta.metadata_nota_url,
                    'metadata_publicacion_url': alerta.metadata_publicacion_url,
                    'created_at': alerta.created_at,
                    'updated_at': alerta.updated_at
                }
            )
        except Exception as e:
            print(f"Error migrando alerta {alerta.title}: {str(e)}")
    
    print("Migración completada exitosamente")

if __name__ == "__main__":
    migrate_data()