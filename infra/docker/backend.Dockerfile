# OnlyWheels API image (Django + gunicorn; the same image runs the Celery worker and beat).
# Build context: backend/   (see infra/docker-compose.prod.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first (cached layer). Uses uv.lock once it is committed.
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --no-dev --locked; else uv sync --no-dev; fi

COPY . .

# Static files are baked into the image and served by WhiteNoise. Dummy values: nothing connects at build time.
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=build-only \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    PAYMENT_PROVIDER=stripe \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media \
    && chown -R app:app /app
USER app

ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
