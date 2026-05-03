# KashFlow System

KashFlow System is a Django full-stack MVP for managing multiple business projects, importing arbitrary Excel workbooks, preserving raw rows, mapping important columns into core tables, and exposing secure dashboards and APIs.

## Stack

- Django, Django REST Framework, Django Templates
- PostgreSQL, Redis, Celery
- HTMX-ready templates, Alpine.js, Tailwind CSS, Chart.js
- pandas, openpyxl
- django-filter, drf-spectacular, django-import-export, Jazzmin admin

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Put the ZeptoMail password in `EMAIL_HOST_PASSWORD` inside `.env`. Do not commit real credentials.

3. Start services:

```bash
docker compose up --build
```

4. Run migrations:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

5. Create an admin user:

```bash
docker compose exec web python manage.py createsuperuser
```

6. Seed demo data:

```bash
docker compose exec web python manage.py seed_demo
```

Open:

- Web app: http://localhost:8000/dashboard/
- Admin: http://localhost:8000/admin/
- Swagger docs: http://localhost:8000/api/docs/

## Excel Import Flow

1. Create a project.
2. Go to `/imports/upload/`.
3. Upload an `.xlsx` file.
4. Review detected sheets and preview rows.
5. Map Excel columns to system fields.
6. Run import.

Every imported row is stored in `RawImportedRow`. Known mappings can create finance transactions; unknown data is stored in `Dataset` and `DatasetRow`.

## Permissions

Project access is enforced in backend selectors and queryset filters. Users only see projects where they have an active `ProjectMember` record, unless they are staff/superuser.

## Useful Commands

```bash
docker compose exec web python manage.py test
docker compose exec web python manage.py shell
docker compose exec celery celery -A config worker -l info
```

## MVP Coverage

- Login/logout
- Responsive RTL layout
- Global and project dashboards
- Project CRUD basics
- Project members and permissions
- Finance accounts and transactions
- Excel upload, workbook analysis, preview, mapping, import, rollback services
- Dataset JSON layer
- Audit log
- Django Admin
- Swagger API docs
