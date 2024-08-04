#!/bin/bash

# Navigate to project directory
cd /home/site/wwwroot

# Create virtual environment
python3 -m venv antenv

# Activate virtual environment
source antenv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files (if needed)
python manage.py collectstatic --noinput

# Apply migrations (if needed)
python manage.py migrate