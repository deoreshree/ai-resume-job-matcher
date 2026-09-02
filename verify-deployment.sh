#!/bin/bash

# Deployment Verification Script
# This script checks if the deployment is working correctly

echo "🔍 Deployment Verification"
echo "=========================="

# Check if application is running
echo "🧪 Testing application health..."
if curl -s http://localhost:5000/api/roles > /dev/null; then
    echo "✅ Application is responding"
else
    echo "❌ Application is not responding"
    exit 1
fi

# Test API endpoints
echo "🧪 Testing API endpoints..."

# Test /api/roles
echo "  Testing /api/roles..."
roles_response=$(curl -s http://localhost:5000/api/roles)
if echo "$roles_response" | grep -q "roles"; then
    echo "  ✅ /api/roles working"
else
    echo "  ❌ /api/roles failed"
fi

# Test static files
echo "🧪 Testing static files..."
if curl -s http://localhost:5000/static/css/style.css > /dev/null; then
    echo "  ✅ CSS file accessible"
else
    echo "  ❌ CSS file not accessible"
fi

if curl -s http://localhost:5000/static/js/app.js > /dev/null; then
    echo "  ✅ JavaScript file accessible"
else
    echo "  ❌ JavaScript file not accessible"
fi

# Test main page
echo "🧪 Testing main page..."
if curl -s http://localhost:5000/ | grep -q "Resume"; then
    echo "  ✅ Main page accessible"
else
    echo "  ❌ Main page not accessible"
fi

echo ""
echo "✅ Deployment verification complete!"
echo "🌐 Access your application at: http://localhost:5000"