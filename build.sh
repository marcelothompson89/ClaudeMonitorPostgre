#!/usr/bin/env bash
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Instalar Playwright y navegadores con todas las dependencias del sistema
echo "Instalando Playwright y navegadores..."
pip install playwright==1.40.0  # Especificar versión estable
python -m playwright install-deps
python -m playwright install chromium --with-deps

# Verificar que los navegadores se instalaron correctamente
echo "Verificando instalación..."
ls -la /opt/render/.cache/ms-playwright/ || echo "No se encontró el directorio de Playwright"

# Ejecutar collectstatic y migraciones
python manage.py collectstatic --no-input --clear
python manage.py migrate
