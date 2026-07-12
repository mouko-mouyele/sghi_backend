#!/bin/bash
# Build Flutter Web (local ou CI)
set -o errexit

API_URL="${SGHL_API_URL:-https://sghi-backend.onrender.com/api/v1}"
BASE_HREF="${BASE_HREF:-/sghi_backend/}"

echo "=== SGHL Mobile Web — build ==="
echo "API: $API_URL"
echo "Base href: $BASE_HREF"

cd "$(dirname "$0")"
flutter pub get
flutter build web --release \
  --base-href="$BASE_HREF" \
  --dart-define=SGHL_API_URL="$API_URL"

echo "=== OK : build/web ==="
