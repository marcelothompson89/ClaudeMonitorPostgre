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

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Build for deployment (Linux/Render)
./build.sh
```

## Architecture

### Django Apps

- **alertas** - Core app: models (`Alerta`, `Keyword`, `Source`, `EmailAlertConfig`), views for browsing/filtering alerts, keyword management, email alert configuration, and email delivery via `services.py`.
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

### API Authentication

`POST /api/run-scrapers/` requires `X-API-Key` header validated with `hmac.compare_digest` against `SCRAPER_API_TOKEN` env var.

## Database

PostgreSQL on Supabase. Config via `python-decouple` reading `.env` vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. A legacy SQLite DB (`alerts2.db`) is configured as `old_db` but not actively used.

**Key models**: `Alerta` (core alert data), `Keyword` (user search terms, unique per user), `EmailAlertConfig` (scheduled email filters), `Source` (data source registry), `ScraperLog` (execution audit trail).

## Deployment

Hosted on Render (`monitorregulatoriomt.onrender.com`). Uses Gunicorn (WSGI), WhiteNoise for static files. `build.sh` runs pip install, playwright install, collectstatic, and migrate.

## Environment Variables

Required in `.env`: `SECRET_KEY`, `DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `SCRAPER_API_TOKEN`.

## Scraper Naming Convention

Scraper files follow `<topic>_<country_code>.py` pattern (e.g., `anmat_noti_ar.py`, `anvisa_normas_br.py`). Country codes: `ar` (Argentina), `br` (Brazil), `cl` (Chile), `co` (Colombia), `mx` (Mexico), `pe` (Peru), `pa` (Panama), `cr` (Costa Rica), `do` (Dominican Republic), `gt` (Guatemala), `cam` (Central America), `reg` (regional), `glo` (global).
