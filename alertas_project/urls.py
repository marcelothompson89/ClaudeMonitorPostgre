# alertas_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import landing_page, register_view, logout_view
from alertas.views import CustomLoginView  # Importar desde alertas.views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('alertas/', include('alertas.urls')),
    path('', landing_page, name='landing'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', register_view, name='register'), 
    path('logout/', logout_view, name='logout'), 
    path('scrapers/', include('scrapers.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

