from django.db import migrations, models
import hashlib

def generate_content_hash(apps, schema_editor):
    """Generar hash para registros existentes"""
    Alerta = apps.get_model('alertas', 'Alerta')
    for alerta in Alerta.objects.all():
        content_to_hash = f"{alerta.title}|{alerta.description}|{alerta.source_url}"
        alerta.content_hash = hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()
        try:
            alerta.save()
        except:
            # Si hay duplicados, eliminar este registro
            alerta.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('alertas', '0004_emailalertconfig_and_more'),
    ]

    operations = [
        # Eliminar los constraints existentes
        migrations.RemoveConstraint(
            model_name='alerta',
            name='unique_alerta_url_title_date',
        ),
        migrations.RemoveConstraint(
            model_name='alerta',
            name='unique_alerta_title_date',
        ),
        
        # Agregar el campo hash
        migrations.AddField(
            model_name='alerta',
            name='content_hash',
            field=models.CharField(max_length=64, null=True, editable=False),
        ),
        
        # Llenar el campo hash para registros existentes
        migrations.RunPython(generate_content_hash),
        
        # Hacer el campo único
        migrations.AlterField(
            model_name='alerta',
            name='content_hash',
            field=models.CharField(max_length=64, unique=True, editable=False),
        ),
    ]