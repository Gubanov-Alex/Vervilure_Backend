FROM python:3.12-slim

# Install system dependencies including gosu for user switching
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-traditional \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.1.3

# Configure Poetry environment
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    DOCKER_CONTAINER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (for better caching)
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Create user with dynamic UID/GID matching host
ARG USER_ID=1000
ARG GROUP_ID=1000

# Create group and user with specific IDs
RUN groupadd --gid $GROUP_ID django \
    && useradd --uid $USER_ID --gid django --shell /bin/bash --create-home django

# Create directories with proper permissions
# ВАЖНО: Создаём все директории, включая migrations
RUN mkdir -p /app/logs /app/static /app/staticfiles /app/media /app/templates \
    /app/src/apps/accounts/migrations \
    /app/src/apps/orders/migrations \
    /app/src/apps/products/migrations \
    /app/src/apps/cart/migrations \
    /app/src/apps/inventory/migrations \
    /app/src/apps/shipping/migrations \
    /app/src/apps/payments/migrations \
    /app/src/apps/reviews/migrations \
    /app/src/apps/analytics/migrations \
    && touch /app/src/apps/accounts/migrations/__init__.py \
    /app/src/apps/orders/migrations/__init__.py \
    /app/src/apps/products/migrations/__init__.py \
    /app/src/apps/cart/migrations/__init__.py \
    /app/src/apps/inventory/migrations/__init__.py \
    /app/src/apps/shipping/migrations/__init__.py \
    /app/src/apps/payments/migrations/__init__.py \
    /app/src/apps/reviews/migrations/__init__.py \
    /app/src/apps/analytics/migrations/__init__.py

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy application files
COPY . .

# Fix permissions comprehensively
RUN chown -R django:django /app \
    && chmod +x /app/manage.py \
    && find /app -type d -name "migrations" -exec chown -R django:django {} \; \
    && find /app -type d -name "migrations" -exec chmod -R 755 {} \; \
    && find /app -name "*.py" -exec chmod 644 {} \; \
    && chmod 755 /app/src /app/src/apps

# Switch to non-root user
USER django

EXPOSE 8000 5678

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
