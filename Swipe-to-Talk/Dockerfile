# Avatars API (Django) — build from repo root:
#   docker build -t voice-avatars-api .
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY config/ config/
COPY voice_avatars/ voice_avatars/

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings
EXPOSE 8000

# Migrate then serve. Override CMD for gunicorn in production if needed.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
