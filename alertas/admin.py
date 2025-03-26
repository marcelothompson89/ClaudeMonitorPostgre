# alertas/admin.py
from django.contrib import admin
from .models import Keyword, Source, Alerta

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('word', 'user', 'active', 'created_at')
    list_filter = ('active', 'user')
    search_fields = ('word', 'user__username', 'user__email')

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'scraper_type', 'active', 'last_scraped')
    list_filter = ('active', 'scraper_type')
    search_fields = ('name', 'url')

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('title', 'institution', 'country', 'source_type', 'presentation_date')
    list_filter = ('institution', 'country', 'source_type')
    search_fields = ('title', 'description')
    date_hierarchy = 'presentation_date'