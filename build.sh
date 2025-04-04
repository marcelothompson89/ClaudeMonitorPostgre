#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
playwright install chromium
# Ejecuta collectstatic primero (y usa --clear)
python manage.py collectstatic --no-input --clear
python manage.py migrate

