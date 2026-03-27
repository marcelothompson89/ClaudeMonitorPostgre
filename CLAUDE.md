# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Regulatory news monitoring system for Latin American health/pharmaceutical institutions. Scrapes 70+ government and regulatory websites, stores alerts in PostgreSQL (Supabase), and delivers filtered content via web UI and scheduled email alerts.

**Language**: Spanish (UI, code comments, variable names). All user-facing text is in Spanish.

## Commands

```bash
# Development server
python manage.py runserver

# Run all scrapers
python manage.py run_scrapers

# Run a specific scraper
python manage.py run_scrapers --scraper=<scraper_id>

# List available scrapers
python manage.py run_scrapers --list

# Send scheduled email alerts
python manage.py send_scheduled_alerts

# Import events from Excel calendar
python manage.py import_eventos

# Import events (clear existing first)
python manage.py import_eventos --limpiar

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Build for deployment (Linux/Render)
./build.sh
```

## Architecture

### Django Apps

- **alertas** - Core app: models (`Alerta`, `Keyword`, `Source`, `EmailAlertConfig`, `Evento`), views for browsing/filtering alerts, keyword management, email alert configuration, email delivery via `services.py`, and event calendar.
- **scrapers** - Scraping engine: individual scraper modules in `scrapers/scrapers/`, orchestration in `tasks.py`, execution logs via `ScraperLog` model, staff-only dashboard for monitoring.
- **alertas_project** - Django project config, root URL routing, landing page, auth views.

### Scraper System

Each scraper is an independent async function in `scrapers/scrapers/<name>.py` following this pattern:
1. Async function `scrape_<name>()` fetches HTML via `httpx`/`playwright`/`selenium`
2. Parses with `BeautifulSoup`
3. Returns a list of dicts with keys: `title`, `description`, `source_url`, `source_type`, `category`, `country`, `institution`, `presentation_date`, optionally `metadata`

`scrapers/tasks.py` contains:
- `AVAILABLE_SCRAPERS` dict - registry mapping scraper IDs to their module/function/metadata
- `run_scraper(scraper_id)` - dynamic import via `importlib`, runs async function with `asyncio.run()`, saves to DB
- `run_all_scrapers()` - iterates all registered scrapers sequentially
- `save_items_to_db(items)` - `Alerta.objects.update_or_create()` with deduplication by `source_url` + `title` + `presentation_date`

**To add a new scraper**: create `scrapers/scrapers/<name>.py` with an async `scrape_<name>()` function, then register it in `AVAILABLE_SCRAPERS` in `tasks.py`.

### Deduplication

`Alerta.content_hash` is a SHA256 of `title|description|source_url`, auto-generated in the model's `save()` method. The `content_hash` field has a unique constraint.

### Email Alerts

`EmailAlertConfig` stores per-user filter combinations (keywords, country, institution, category, frequency). The `send_scheduled_alerts` management command checks each active config, queries matching `Alerta` records, renders `email/alert_email.html`, and sends via Gmail SMTP.

### Scheduled Execution (GitHub Actions)

- **Scrapers**: every 6 hours (`.github/workflows/run_scrapers.yml`)
- **Email alerts**: daily at 9 AM UTC (`.github/workflows/send_scheduled_alerts.yml`)
- DB credentials injected from GitHub Secrets; uses Supabase session pooler (`aws-0-sa-east-1.pooler.supabase.com`)

### Event Calendar

Shared calendar at `/alertas/calendario/` displaying institutional events. Uses FullCalendar.js (CDN) for month/week views with side panel for automatic event detection. All authenticated users can create, view, edit, and delete events.

#### Core Calendar Features
- **Model**: `Evento` with fields: `titulo`, `descripcion`, `fecha_inicio`, `fecha_fin`, `tipo` (evento/comité/político/feriado/conferencia/otro), `ubicacion`, `created_by`
- **API endpoint**: `/alertas/calendario/api/eventos/` returns JSON for FullCalendar (filtered by `start`/`end` params)
- **CRUD Operations**:
  - Create: AJAX POST to `/alertas/calendario/evento/crear/`
  - Edit: Click event → "Editar" button opens modal with pre-filled form → AJAX POST to `/alertas/calendario/evento/<pk>/editar/`
  - Delete: Click event → "Eliminar" button → AJAX POST to `/alertas/calendario/evento/<pk>/eliminar/`
- **Import**: `python manage.py import_eventos` loads events from `CALENDARIO EVENTOS & COMITÉS 2026 (1).xlsx` using `openpyxl`. Uses `get_or_create` on `titulo` + `fecha_inicio` to avoid duplicates.
- **Colors by type**: evento=#002D62, comité=#198754, político=#dc3545, feriado=#ffc107, conferencia=#0dcaf0, otro=#6c757d

#### Automatic Event Detection (from scraped alerts)

**Purpose**: Automatically identifies potential events in scraped alerts and displays them in a sidebar for easy addition to the calendar.

**Detection Logic** (`alertas/utils.py`):
- `contains_event_keywords(text)`: Filters alerts containing 25+ Spanish event keywords (congreso, conferencia, seminario, webinar, taller, workshop, foro, reunión, sesión, simposio, jornada, encuentro, convocatoria, inscripción, registro, charla, curso, capacitación, cumbre, summit, mesa redonda, panel, debate, expo, feria, exhibición, lanzamiento, presentación, inauguración, ceremonia, asamblea, cita, audiencia, consulta pública)
- `extract_dates_from_text(text)`: Uses `dateparser` library to extract event dates from Spanish text. Handles ranges like "del 15 al 20 de marzo de 2026" and single dates. Returns `{'start_date': date, 'end_date': date}`.
- `suggest_event_type(title, description)`: Suggests event type (conferencia, comité, político, feriado, evento) based on keyword patterns

**API & Views**:
- `GET /alertas/calendario/api/eventos-potenciales/` → `api_eventos_potenciales()`: Returns up to 20 potential events from the last 30 days. Queries last 100 alerts, filters by keywords, extracts dates, and returns JSON with: `id`, `title`, `description`, `source`, `country`, `category`, `source_url`, `detected_start_date`, `detected_end_date`, `suggested_type`
- `POST /alertas/calendario/alerta/<alerta_id>/convertir/` → `convertir_alerta_a_evento()`: Converts an alert to a calendar event (endpoint exists but currently unused; conversion happens via modal form)

**UI Implementation**:
- **Two-column layout**: Calendar (8 cols) + Sidebar panel (4 cols) showing detected events
- **Event cards**: Display title, description, source, country, detected dates, link to original source
- **One-click add**: "Agregar al Calendario" button opens creation modal with pre-filled data (title, description, dates, suggested type)
- **Data attributes**: Uses `dataset` attributes and event delegation to safely handle special characters (quotes, accents, symbols) in event titles

**Dependencies**: Requires `dateparser==1.2.0` for Spanish date extraction

### API Authentication

`POST /api/run-scrapers/` requires `X-API-Key` header validated with `hmac.compare_digest` against `SCRAPER_API_TOKEN` env var.

## Database

PostgreSQL on Supabase. Config via `python-decouple` reading `.env` vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. A legacy SQLite DB (`alerts2.db`) is configured as `old_db` but not actively used.

**Key models**: `Alerta` (core alert data), `Keyword` (user search terms, unique per user), `EmailAlertConfig` (scheduled email filters), `Source` (data source registry), `ScraperLog` (execution audit trail), `Evento` (calendar events with type, dates, location).

## Deployment

Hosted on Render (`monitorregulatoriomt.onrender.com`). Uses Gunicorn (WSGI), WhiteNoise for static files. `build.sh` runs pip install, playwright install, collectstatic, and migrate.

## Environment Variables

Required in `.env`: `SECRET_KEY`, `DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `SCRAPER_API_TOKEN`.

## Scraper Naming Convention

Scraper files follow `<topic>_<country_code>.py` pattern (e.g., `anmat_noti_ar.py`, `anvisa_normas_br.py`). Country codes: `ar` (Argentina), `br` (Brazil), `cl` (Chile), `co` (Colombia), `mx` (Mexico), `pe` (Peru), `pa` (Panama), `cr` (Costa Rica), `do` (Dominican Republic), `gt` (Guatemala), `cam` (Central America), `reg` (regional), `glo` (global).
