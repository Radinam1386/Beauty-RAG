#!/usr/bin/env bash
# استارت همزمان بک‌اند و فرانت برای توسعه
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== BeautyBoss AI dev ==="
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:4200/chat"

# دیتابیس
if ! pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
  echo "PostgreSQL روی 5432 روشن نیست. brew services start postgresql@16"
  brew services start postgresql@16 || true
  sleep 2
fi

# migration
env/bin/python -m alembic upgrade head

# بک‌اند
echo "starting backend..."
env/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACK=$!

# فرانت
echo "starting frontend..."
cd frontend
if [ ! -d node_modules ]; then
  npm install
fi
./node_modules/.bin/ng serve --host 0.0.0.0 --port 4200 --no-open &
FRONT=$!

trap "kill $BACK $FRONT 2>/dev/null" EXIT
echo "PIDs: backend=$BACK frontend=$FRONT"
wait
