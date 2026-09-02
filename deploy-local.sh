#!/bin/bash

# AI Resume & Job Matcher - Local Deployment Script
# This script helps you deploy the application locally using Docker

set -e

echo "🚀 AI Resume & Job Matcher - Local Deployment"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Start the containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for the application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is running
if curl -s http://localhost:5000/api/roles > /dev/null; then
    echo "✅ Application is running successfully!"
    echo "🌐 Access the application at: http://localhost:5000"
    echo "📊 View logs with: docker-compose logs -f"
    echo "🛑 Stop the application with: docker-compose down"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    docker-compose logs
    exit 1
fi