#!/bin/bash
set -e

echo "🚀 Starting Vervilure application..."

# Wait for database
echo "⏳ Waiting for database..."
while ! nc -z db 5432; do
  echo "Database not ready, waiting..."
  sleep 2
done
echo "✅ Database is ready!"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
  echo "Redis not ready, waiting..."
  sleep 2
done
echo "✅ Redis is ready!"

# Django initialization for web service
if [ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
  echo "🔧 Initializing Django web service..."
  python manage.py migrate --noinput || echo "⚠️ Migration failed"
  python manage.py collectstatic --noinput || echo "⚠️ Static collection failed"
fi

# Execute the command
echo "🎯 Executing: $@"
exec "$@"
