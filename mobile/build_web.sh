#!/bin/bash
# Build Flutter Web pour Render (site statique gratuit)
set -o errexit

API_URL="${SGHL_API_URL:-https://sghi-backend.onrender.com/api/v1}"

echo "=== SGHL Mobile Web — build production ==="
echo "API: $API_URL"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Installation Flutter (stable)..."
  git clone https://github.com/flutter/flutter.git -b stable --depth 1 /opt/flutter
  export PATH="/opt/flutter/bin:$PATH"
  flutter config --enable-web --no-analytics
  flutter precache --web
fi

flutter --version
cd mobile
flutter pub get
flutter build web --release \
  --dart-define=SGHL_API_URL="$API_URL" \
  --web-renderer canvaskit

echo "=== Build terminé : mobile/build/web ==="
