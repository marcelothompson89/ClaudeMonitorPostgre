# alertas/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['source_url', 'title', 'presentation_date'],
                name='unique_alerta_url_title_date',
                condition=models.Q(source_url__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['title', 'presentation_date'],
                name='unique_alerta_title_date',
                condition=models.Q(source_url__isnull=True) | models.Q(source_url='')
            )
        ]

    def __str__(self):
        return self.title