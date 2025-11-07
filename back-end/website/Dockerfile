# ==========================
# Base image: Python + Node for dev
# ==========================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEV=true

WORKDIR /app

# --------------------------
# System dependencies
# --------------------------
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev curl git && \
    rm -rf /var/lib/apt/lists/*

# --------------------------
# Python dependencies
# --------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------
# Node (for Tailwind/DaisyUI)
# --------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm

# --------------------------
# Copy project files
# --------------------------
COPY . .

# Expose port
EXPOSE 8000

# --------------------------
# Dev / Prod command
# --------------------------
CMD if [ "$DEV" = "true" ]; then \
        echo "🟢 Dev mode: npm install + Tailwind watch + Django server"; \
        python3 manage.py makemigrations && python3 manage.py migrate --noinput; \
        npm install; \
        npx tailwindcss -i ./army_app/static/css/input.css -o ./army_app/static/css/output.css --watch & \
        python manage.py runserver 0.0.0.0:8000; \
    else \
        echo "🚀 Production mode: Build Tailwind + collect static"; \
        npm ci; \
        npx tailwindcss -i ./army_app/static/css/input.css -o ./army_app/static/css/output.css --minify; \
        python manage.py collectstatic --noinput; \
        python3 manage.py makemigrations && python manage.py migrate --noinput; \
        gunicorn website.wsgi:application --bind 0.0.0.0:8000; \
    fi
