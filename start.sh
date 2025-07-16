#!/bin/bash

# Media Agency Lead Management System Startup Script

echo "Starting Media Agency Lead Management System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database if it doesn't exist
if [ ! -f "instance/media_agency.db" ]; then
    echo "Initializing database..."
    python3 init_db.py
fi

# Start the application
echo "Starting Flask application..."
echo "Visit http://localhost:5001 to access the application"
echo "Default login: admin / admin123"
echo "Press Ctrl+C to stop the server"
python3 run.py