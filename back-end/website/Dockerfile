# ---- Base image ----
FROM python:3.12-slim

# ---- Environment setup ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---- Workdir ----
WORKDIR /app

# ---- Install system dependencies ----
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# ---- Install Python dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy project files ----
COPY . .

# ---- Collect static files (only used in production) ----
RUN python manage.py collectstatic --noinput || true

# ---- Expose port ----
EXPOSE 8000

# ---- Switch between dev & prod ----
ENV DEV=true
CMD if [ "$DEV" = "true" ]; then \
        echo "🟢 Starting Django development server..." && \
        python manage.py runserver 0.0.0.0:8000; \
    else \
        echo "🚀 Starting Gunicorn production server..." && \
        gunicorn website.wsgi:application --bind 0.0.0.0:8000; \
    fi
