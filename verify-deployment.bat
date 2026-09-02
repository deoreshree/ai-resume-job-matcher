@echo off
REM Deployment Verification Script for Windows
REM This script checks if the deployment is working correctly

echo ==============================================
echo Deployment Verification
echo ==============================================
echo.

REM Check if application is running
echo 🧪 Testing application health...
curl -s http://localhost:5000/api/roles >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Application is responding
) else (
    echo ❌ Application is not responding
    pause
    exit /b 1
)

REM Test API endpoints
echo 🧪 Testing API endpoints...

REM Test /api/roles
echo   Testing /api/roles...
curl -s http://localhost:5000/api/roles > temp_response.txt
findstr /C:"roles" temp_response.txt >nul
if %errorlevel% equ 0 (
    echo   ✅ /api/roles working
) else (
    echo   ❌ /api/roles failed
)
del temp_response.txt

REM Test static files
echo 🧪 Testing static files...
curl -s http://localhost:5000/static/css/style.css >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ CSS file accessible
) else (
    echo   ❌ CSS file not accessible
)

curl -s http://localhost:5000/static/js/app.js >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ JavaScript file accessible
) else (
    echo   ❌ JavaScript file not accessible
)

REM Test main page
echo 🧪 Testing main page...
curl -s http://localhost:5000/ > temp_page.txt
findstr /C:"Resume" temp_page.txt >nul
if %errorlevel% equ 0 (
    echo   ✅ Main page accessible
) else (
    echo   ❌ Main page not accessible
)
del temp_page.txt

echo.
echo ✅ Deployment verification complete!
echo 🌐 Access your application at: http://localhost:5000
echo.
pause