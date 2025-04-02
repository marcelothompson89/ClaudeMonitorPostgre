# alertas/urls.py
from django.urls import path
from . import views
from .views import register_view, CustomLoginView

app_name = 'alertas'

urlpatterns = [
    path('', views.alertas_list, name='alertas_list'),
    path('api/keywords/', views.get_keywords_for_user, name='get_keywords'),
    
    # Nuevas URLs para gestionar palabras clave
    path('mis-palabras-clave/', views.manage_keywords, name='manage_keywords'),
    path('mis-palabras-clave/<int:keyword_id>/toggle/', views.toggle_keyword_status, name='toggle_keyword'),
    path('mis-palabras-clave/<int:keyword_id>/eliminar/', views.delete_keyword, name='delete_keyword'),
    path('toggle-filtro-keywords/', views.toggle_keyword_filter, name='toggle_keyword_filter'),

    # URLs para la configuración de alertas por correo
    path('email-alerts/', views.email_alert_config_list, name='email_alert_configs'),
    path('email-alerts/new/', views.email_alert_config_create, name='email_alert_config_create'),
    path('email-alerts/<int:pk>/edit/', views.email_alert_config_edit, name='email_alert_config_edit'),
    path('email-alerts/<int:pk>/delete/', views.email_alert_config_delete, name='email_alert_config_delete'),
    path('email-alerts/<int:pk>/send/', views.send_email_alert, name='send_email_alert'),
    
    # Nueva URL para obtener las instituciones por país
    path('api/institutions-by-country/', views.get_institutions_by_country, name='get_institutions_by_country'),
]