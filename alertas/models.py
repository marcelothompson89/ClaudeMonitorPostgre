# alertas/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib

class Keyword(models.Model):
    word = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keywords')
    created_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['word', 'user']

    def __str__(self):
        return self.word

class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(unique=True)
    scraper_type = models.CharField(max_length=50)  # Tipo de scraper a usar (ispch, etc.)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_scraped = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Alerta(models.Model):
    # Aumenta la longitud de estos campos
    title = models.CharField(max_length=500)  # Cambiar de 255 a 500
    description = models.TextField()
    source_type = models.CharField(max_length=300)  # Aumentar según sea necesario
    category = models.CharField(max_length=300)
    country = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500)
    institution = models.CharField(max_length=300)
    metadata_nota_url = models.URLField(max_length=500, blank=True, null=True)
    metadata_publicacion_url = models.URLField(max_length=500, blank=True, null=True)
    presentation_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content_hash = models.CharField(max_length=64, unique=True, editable=False)

    class Meta:
       
       pass

    def save(self, *args, **kwargs):
        # Generar hash antes de guardar
        content_to_hash = f"{self.title}|{self.description}|{self.source_url}"
        self.content_hash = hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# Envio de Alertas por mail modelo

class EmailAlertConfig(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_alert_configs')
    name = models.CharField(max_length=100, verbose_name="Nombre de la configuración")
    active = models.BooleanField(default=True, verbose_name="Activo")
    
    # Filtros
    keywords = models.ManyToManyField(Keyword, blank=True, related_name='email_configs', verbose_name="Palabras clave")
    source_type = models.CharField(max_length=300, blank=True, verbose_name="Tipo de fuente")
    category = models.CharField(max_length=300, blank=True, verbose_name="Categoría")
    country = models.CharField(max_length=300, blank=True, verbose_name="País")
    institution = models.CharField(max_length=300, blank=True, verbose_name="Institución")
    
    # Filtros de fecha
    days_back = models.IntegerField(default=1, verbose_name="Días hacia atrás")
    
    # Configuración de correo
    email = models.EmailField(verbose_name="Correo electrónico para recibir alertas")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='daily', verbose_name="Frecuencia")
    
    # Seguimiento
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sent = models.DateTimeField(null=True, blank=True, verbose_name="Último envío")
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


class Evento(models.Model):
    TIPO_CHOICES = [
        ('evento', 'Evento'),
        ('comite', 'Comité'),
        ('politico', 'Político'),
        ('feriado', 'Feriado'),
        ('conferencia', 'Conferencia'),
        ('otro', 'Otro'),
    ]

    titulo = models.CharField(max_length=500, verbose_name="Título")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de fin")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='evento', verbose_name="Tipo")
    ubicacion = models.CharField(max_length=300, blank=True, verbose_name="Ubicación")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fecha_inicio']

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio})"