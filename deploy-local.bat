@echo off
REM AI Resume & Job Matcher - Local Deployment Script for Windows
REM This script helps you deploy the application locally using Docker

echo ==============================================
echo AI Resume & Job Matcher - Local Deployment
echo ==============================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo Visit: https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

echo ✅ Docker is installed
echo.

REM Stop any existing containers
echo 🛑 Stopping any existing containers...
docker-compose down 2>nul

REM Build the Docker image
echo 🔨 Building Docker image...
docker-compose build

if %errorlevel% neq 0 (
    echo ❌ Docker build failed. Please check the error messages above.
    pause
    exit /b 1
)

REM Start the containers
echo 🚀 Starting containers...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ❌ Failed to start containers. Please check the error messages above.
    pause
    exit /b 1
)

REM Wait for the application to start
echo ⏳ Waiting for application to start...
timeout /t 10 /nobreak >nul

REM Check if the application is running
echo 🧪 Testing application...
curl -s http://localhost:5000/api/roles >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ✅ Application is running successfully!
    echo 🌐 Access the application at: http://localhost:5000
    echo 📊 View logs with: docker-compose logs -f
    echo 🛑 Stop the application with: docker-compose down
    echo.
) else (
    echo.
    echo ❌ Application failed to start. Check logs with: docker-compose logs
    docker-compose logs
    pause
    exit /b 1
)

pause