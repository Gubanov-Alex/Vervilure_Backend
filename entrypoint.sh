#!/bin/bash

# Fixed entrypoint WITHOUT chmod operations on bind mounts
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

# Function to ensure migrations directories exist (WITHOUT chmod on bind mounts)
ensure_migrations_dirs() {
    echo -e "${YELLOW}🔧 Ensuring migrations directories exist...${NC}"

    # Define all Django apps that need migrations
    APPS=(
        "accounts"
        "orders"
        "products"
        "cart"
        "inventory"
        "shipping"
        "payments"
        "reviews"
        "analytics"
    )

    # Create migrations directories for each app
    for app in "${APPS[@]}"; do
        migrations_dir="/app/src/apps/${app}/migrations"

        # Create directory if it doesn't exist
        if [ ! -d "$migrations_dir" ]; then
            echo "Creating migrations directory: $migrations_dir"
            mkdir -p "$migrations_dir" 2>/dev/null || {
                echo "⚠️  Cannot create $migrations_dir (bind mount read-only)"
                continue
            }
        fi

        # Ensure __init__.py exists
        if [ ! -f "$migrations_dir/__init__.py" ]; then
            echo "Creating __init__.py in: $migrations_dir"
            touch "$migrations_dir/__init__.py" 2>/dev/null || {
                echo "⚠️  Cannot create __init__.py in $migrations_dir (bind mount read-only)"
                continue
            }
        fi

        # Skip chmod operations on bind mounted directories
        echo "✓ Directory $migrations_dir ready (bind mount - skipping chmod)"
    done

    echo -e "${GREEN}✅ Migrations directories ready!${NC}"
}

# Function to fix permissions if running as root (skip bind mounts)
fix_permissions() {
    if [ "$(id -u)" = "0" ]; then
        echo -e "${YELLOW}🔧 Running as root, fixing ownership and switching to django user...${NC}"

        # Fix ownership only of Docker volumes (not bind mounts)
        chown -R django:django /app/logs /app/media /app/static /app/staticfiles 2>/dev/null || true

        # Skip bind mounted directories to avoid permission errors
        echo "ℹ️  Skipping /app/src (bind mount)"

        # Switch to django user for rest of execution
        echo -e "${GREEN}🔄 Switching to django user...${NC}"
        exec gosu django "$0" "$@"
    fi
}

# Function to run Django checks
run_django_checks() {
    echo -e "${YELLOW}🧪 Running Django system checks...${NC}"

    # Basic check
    python manage.py check --deploy 2>/dev/null || python manage.py check

    echo -e "${GREEN}✅ Django checks passed!${NC}"
}

# Main execution flow
main() {
    # Fix permissions if needed (will exec if running as root)
    fix_permissions

    # Ensure migrations directories exist
    ensure_migrations_dirs

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

# Run main function
main "$@"
