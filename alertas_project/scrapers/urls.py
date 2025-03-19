from django.urls import path
from . import views

app_name = 'scrapers'

urlpatterns = [
    path('', views.scrapers_dashboard, name='dashboard'),
    path('run-all/', views.run_scrapers_manually, name='run_all'),
    path('run/<str:scraper_id>/', views.run_specific_scraper, name='run_specific'),
]