#!/bin/bash
set -e

echo "🚀 Starting Django application..."
echo "👤 Running as user: $(whoami) (UID: $(id -u), GID: $(id -g))"
echo "📁 Working directory: $(pwd)"
echo "📂 Directory contents:"
ls -la

# Function to check service availability
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "⏳ Waiting for $service_name..."
    while ! nc -z "$host" "$port" 2>/dev/null; do
        echo "Waiting for $service_name at $host:$port..."
        sleep 2
    done
    echo "✅ $service_name is ready!"
}

# Wait for services
wait_for_service "${DB_HOST:-db}" "${DB_PORT:-5432}" "PostgreSQL"
wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"

# Check Python environment
echo "🐍 Python environment:"
python --version
echo "📦 Installed packages:"
pip list | head -20

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    echo "❌ ERROR: manage.py not found!"
    echo "📁 Current directory contents:"
    ls -la
    exit 1
fi

# Basic Django checks for web service
if [[ "$*" == *"manage.py"* ]] || [[ "$*" == *"runserver"* ]] || [[ "$*" == *"python"* ]]; then
    echo "🧪 Running Django system checks..."
    python manage.py check --verbosity 2 || {
        echo "❌ Django checks failed!"
        echo "Attempting basic imports..."
        python -c "import django; print(f'Django {django.__version__} imported successfully')"
        python -c "import sys; print(f'Python path: {sys.path}')"
        exit 1
    }
    echo "✅ Django checks passed!"
fi

# Execute the provided command
echo "🎯 Executing command: $*"
exec "$@"
