FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.1.3

# Configure Poetry to NOT create a virtual environment inside the container
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml poetry.lock ./
# Устанавливаем ВСЕ зависимости для разработки
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create README.md if not exists (fix Poetry installation issue)
RUN touch README.md

# Create non-root user
RUN groupadd --gid 1000 django \
    && useradd --uid 1000 --gid django --shell /bin/bash --create-home django

# Change ownership
RUN chown -R django:django /app

USER django

EXPOSE 8000

# Use Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]