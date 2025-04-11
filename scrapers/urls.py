from django.urls import path
from . import views

app_name = 'scrapers'

urlpatterns = [
    path('', views.scrapers_dashboard, name='dashboard'),
    path('run-all/', views.run_scrapers_manually, name='run_all'),
    path('run/<str:scraper_id>/', views.run_specific_scraper, name='run_specific'),
    path('logs/', views.view_scraper_logs, name='logs'),
    path('logs/<int:log_id>/', views.view_scraper_log_detail, name='log_detail'),
    path('api/run-scrapers/', views.run_scrapers_api, name='run-scrapers-api'),
]