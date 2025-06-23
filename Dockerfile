FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-traditional \
    curl \
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

# Create user
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd --gid $GROUP_ID django \
    && useradd --uid $USER_ID --gid django --shell /bin/bash --create-home django

# Create directories
RUN mkdir -p /app/logs /app/static /app/staticfiles /app/media /app/templates

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy application
COPY . .

# Fix permissions
RUN chown -R django:django /app \
    && chmod +x /app/manage.py

USER django

EXPOSE 8000 5678

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
