# alertas/urls.py
from django.urls import path
from . import views

app_name = 'alertas'

urlpatterns = [
    path('', views.alertas_list, name='alertas_list'),
    path('api/keywords/', views.get_keywords_for_user, name='get_keywords'),
    
    # Nuevas URLs para gestionar palabras clave
    path('mis-palabras-clave/', views.manage_keywords, name='manage_keywords'),
    path('mis-palabras-clave/<int:keyword_id>/toggle/', views.toggle_keyword_status, name='toggle_keyword'),
    path('mis-palabras-clave/<int:keyword_id>/eliminar/', views.delete_keyword, name='delete_keyword'),
    path('toggle-filtro-keywords/', views.toggle_keyword_filter, name='toggle_keyword_filter'),
]