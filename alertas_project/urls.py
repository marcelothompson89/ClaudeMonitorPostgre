# alertas_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import landing_page, login_view, register_view
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('alertas/', include('alertas.urls')),
    path('', landing_page, name='landing'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('scrapers/', include('scrapers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import os
print("DEBUG:", settings.DEBUG)
print("STATIC_URL:", settings.STATIC_URL)
print("STATIC_ROOT:", settings.STATIC_ROOT)
print("STATICFILES_DIRS:", settings.STATICFILES_DIRS)
print("STATICFILES_DIRS[0] exists:", os.path.exists(settings.STATICFILES_DIRS[0]))
# Verificar si algunos archivos específicos existen
css_path = os.path.join(settings.STATICFILES_DIRS[0], 'css/styles.css')
print("CSS file exists:", os.path.exists(css_path))