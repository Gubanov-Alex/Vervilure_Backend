#!/bin/bash

# Improved entrypoint with permission handling
set -e

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Django application...${NC}"

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}⏳ Waiting for database...${NC}"
    while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
        echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
        sleep 2
    done
    echo -e "${GREEN}✅ Database is ready!${NC}"
}

# Function to wait for Redis
wait_for_redis() {
    echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"
    while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
        echo "Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
        sleep 2
    done
    echo -e "${GREEN}✅ Redis is ready!${NC}"
}

# Function to fix permissions
fix_permissions() {
    echo -e "${YELLOW}🔧 Checking and fixing permissions...${NC}"

    # Create migrations directories if they don't exist
    find /app/src -name "apps" -type d -exec find {} -name "migrations" -type d \; | while read migrations_dir; do
        if [ ! -d "$migrations_dir" ]; then
            echo "Creating migrations directory: $migrations_dir"
            mkdir -p "$migrations_dir"
        fi

        # Ensure __init__.py exists in migrations directories
        if [ ! -f "$migrations_dir/__init__.py" ]; then
            echo "Creating __init__.py in: $migrations_dir"
            touch "$migrations_dir/__init__.py"
        fi
    done

    # Fix ownership of critical directories (if running as root, switch to django user)
    if [ "$(id -u)" = "0" ]; then
        echo "Running as root, fixing ownership..."
        chown -R django:django /app/src /app/logs /app/media /app/static /app/staticfiles 2>/dev/null || true
        find /app -type d -name "migrations" -exec chown -R django:django {} \; 2>/dev/null || true

        # Switch to django user for rest of execution
        exec gosu django "$0" "$@"
    fi

    # Set proper permissions for current user
    chmod -R 755 /app/src 2>/dev/null || true
    find /app -type d -name "migrations" -exec chmod -R 755 {} \; 2>/dev/null || true

    echo -e "${GREEN}✅ Permissions fixed!${NC}"
}

# Function to run Django checks
run_django_checks() {
    echo -e "${YELLOW}🧪 Running Django system checks...${NC}"

    # Basic check
    python manage.py check --deploy 2>/dev/null || python manage.py check

    # Check if migrations are needed
    if python manage.py showmigrations --plan | grep -q "\[ \]"; then
        echo -e "${YELLOW}⚠️  Unapplied migrations detected${NC}"
    else
        echo -e "${GREEN}✅ All migrations are applied${NC}"
    fi
}

# Main execution flow
main() {
    # Fix permissions first
    fix_permissions

    # Wait for services based on command
    case "$1" in
        "celery")
            wait_for_redis
            wait_for_db
            ;;
        "python"|"poetry")
            # For Django commands, wait for dependencies
            if [[ "$*" == *"manage.py"* ]] || [[ "$*" == *"runserver"* ]]; then
                wait_for_db
                wait_for_redis
                run_django_checks
            fi
            ;;
        *)
            # For any other command, assume it needs both services
            wait_for_db
            wait_for_redis
            ;;
    esac

    echo -e "${GREEN}🎯 Executing command: $*${NC}"

    # Execute the provided command
    exec "$@"
}

# Install gosu if not present (for user switching)
if [ "$(id -u)" = "0" ] && [ ! -x "$(command -v gosu)" ]; then
    echo "Installing gosu for user switching..."
    apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*
fi

# Run main function
main "$@"
