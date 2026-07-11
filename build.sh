#!/bin/bash
set -o errexit

# Install Node.js dependencies and build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Install Python dependencies (already in venv from Render)
pip install -r requirements.txt

# Django setup
echo "Running Django migrations..."
python manage.py migrate

echo "Seeding demo users and hospital data..."
python manage.py seed_demo

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build completed successfully!"
