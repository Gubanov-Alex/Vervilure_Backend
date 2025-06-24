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
# FIXED: Use UID/GID instead of USER_ID/GROUP_ID
ARG UID=1000
ARG GID=1000

# FIXED: Handle root user case properly
RUN if [ "$GID" != "0" ]; then \
        groupadd --gid $GID django; \
    else \
        groupadd django; \
    fi \
    && if [ "$UID" != "0" ]; then \
        useradd --uid $UID --gid django --shell /bin/bash --create-home django; \
    else \
        useradd --gid django --shell /bin/bash --create-home django; \
    fi

# Copy entrypoint script first
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy application files
COPY . .

# Create all necessary directories AFTER copying files
RUN mkdir -p /app/logs /app/static /app/staticfiles /app/media /app/templates \
    && mkdir -p /app/src/apps/accounts/migrations \
    /app/src/apps/orders/migrations \
    /app/src/apps/products/migrations \
    /app/src/apps/cart/migrations \
    /app/src/apps/inventory/migrations \
    /app/src/apps/shipping/migrations \
    /app/src/apps/payments/migrations \
    /app/src/apps/reviews/migrations \
    /app/src/apps/analytics/migrations

# Create __init__.py files in migrations directories
RUN for dir in accounts orders products cart inventory shipping payments reviews analytics; do \
        if [ -d "/app/src/apps/$dir" ]; then \
            mkdir -p "/app/src/apps/$dir/migrations" && \
            touch "/app/src/apps/$dir/migrations/__init__.py"; \
        fi; \
    done

# Create log files
RUN touch /app/logs/django.log /app/logs/celery.log

# Fix ALL permissions in one go
RUN chown -R django:django /app \
    && chmod -R 755 /app \
    && chmod +x /app/manage.py \
    && chmod -R 777 /app/logs \
    && chmod -R 777 /app/src/apps/*/migrations \
    && chmod 666 /app/logs/*.log

# FIXED: Only switch to non-root user if not root
RUN if [ "$UID" != "0" ]; then \
        echo "Switching to django user"; \
    else \
        echo "Running as root user"; \
    fi

# Conditional USER directive
RUN if [ "$UID" != "0" ]; then echo "USER django" > /tmp/user_directive; else echo "# Running as root" > /tmp/user_directive; fi
RUN cat /tmp/user_directive

EXPOSE 8000 5678

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
