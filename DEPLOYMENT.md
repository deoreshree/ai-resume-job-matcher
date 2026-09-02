# AI Resume & Job Matcher - Deployment Guide

This guide provides step-by-step instructions for deploying the AI Resume & Job Matcher application without errors.

## Prerequisites

- Git installed
- Docker installed (for container deployment)
- Cloud platform account (Render, Heroku, Railway, etc.) OR VPS access
- Basic knowledge of command line

## Pre-Deployment Checklist

### 1. Verify Local Setup

```bash
# Navigate to project directory
cd ai-resume-job-matcher

# Run tests to ensure everything works
pytest -v

# Test the application locally
python app.py
```

### 2. Update Configuration Files

#### requirements.txt
Ensure your requirements.txt has compatible versions (already fixed):

```txt
Flask==3.1.3
python-dotenv==1.2.3
python-multipart==0.0.32
Werkzeug==3.1.8
pypdf>=6.0.0
python-docx>=1.1.0
spacy==3.8.16
nltk>=3.10.0
scikit-learn>=1.5.0
numpy>=2.0.0
pandas>=2.2.0
scipy>=1.14.0
sentence-transformers>=3.0.0
torch>=2.4.0
openai==1.3.0
gunicorn>=23.0.0
pytest==9.1.1
requests==2.34.2
```

#### .env File
Create a `.env` file (optional for basic functionality):

```bash
# Copy the example file
cp .env.example .env

# Edit .env if you want AI features (optional)
# OPENAI_API_KEY=your_key_here
# ENABLE_EMBEDDINGS=false
```

## Deployment Options

### Option 1: Render.com (Recommended - Free Tier Available)

#### Step 1: Prepare for Render

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Ready for deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-resume-job-matcher.git
git push -u origin main
```

2. **Verify files are present:**
- `Dockerfile` ✅
- `Procfile` ✅
- `requirements.txt` ✅
- `.env.example` ✅
- `app.py` ✅

#### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) and sign up
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `ai-resume-matcher` (or your preferred name)
   - **Branch**: `main`
   - **Runtime**: Docker
   - **Build Command**: (auto-detected from Dockerfile)
   - **Start Command**: (auto-detected from Dockerfile)

5. **Environment Variables** (Optional):
   - `OPENAI_API_KEY`: Your OpenAI key (if using AI features)
   - `ENABLE_EMBEDDINGS`: `false` (recommended for free tier)

6. Click "Create Web Service"

#### Step 3: Monitor Deployment

- Watch the build logs in Render dashboard
- First deployment may take 5-10 minutes
- Once deployed, you'll get a URL like `https://ai-resume-matcher.onrender.com`

### Option 2: Heroku

#### Step 1: Install Heroku CLI

```bash
# Download and install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli
heroku login
```

#### Step 2: Deploy

```bash
# Create Heroku app
heroku create ai-resume-matcher

# Set buildpack to use Docker
heroku buildpacks:set https://github.com/heroku/heroku-buildpack-docker.git

# Push to Heroku
git push heroku main

# Open the deployed app
heroku open
```

#### Step 3: Configure Environment Variables (Optional)

```bash
heroku config:set OPENAI_API_KEY=your_key_here
heroku config:set ENABLE_EMBEDDINGS=false
```

### Option 3: Docker (VPS/Cloud Server)

#### Step 1: Build Docker Image

```bash
# Build the image
docker build -t ai-resume-matcher .

# Test locally
docker run -p 5000:5000 ai-resume-matcher
```

#### Step 2: Push to Docker Hub (Optional)

```bash
# Tag the image
docker tag ai-resume-matcher yourusername/ai-resume-matcher:latest

# Login to Docker Hub
docker login

# Push the image
docker push yourusername/ai-resume-matcher:latest
```

#### Step 3: Deploy on VPS

```bash
# SSH into your server
ssh user@your-server-ip

# Pull the image
docker pull yourusername/ai-resume-matcher:latest

# Run the container
docker run -d \
  --name ai-resume-matcher \
  -p 80:5000 \
  --restart unless-stopped \
  yourusername/ai-resume-matcher:latest

# Or use docker-compose (recommended)
docker-compose up -d
```

#### Step 4: Create docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    image: yourusername/ai-resume-matcher:latest
    container_name: ai-resume-matcher
    ports:
      - "80:5000"
    restart: unless-stopped
    environment:
      - PORT=5000
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ENABLE_EMBEDDINGS=false
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Option 4: Railway (Simplest)

#### Step 1: Deploy via Railway

1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Docker configuration
5. Add environment variables if needed
6. Click "Deploy"

### Option 5: PythonAnywhere (Traditional Hosting)

#### Step 1: Sign Up

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Create a free account

#### Step 2: Configure

```bash
# In PythonAnywhere console:
git clone https://github.com/YOUR_USERNAME/ai-resume-job-matcher.git
cd ai-resume-job-matcher

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure web app in PythonAnywhere dashboard
# Point to app.py
# Set worker to manual: gunicorn app:app
```

## Post-Deployment Verification

### 1. Health Check

```bash
# Test the deployed application
curl https://your-app-url.com/api/roles
```

Expected response:
```json
{
  "roles": [
    {"title": "Data Scientist"},
    {"title": "Software Engineer"},
    ...
  ]
}
```

### 2. Functional Testing

1. **Upload a test resume** (PDF or DOCX)
2. **Select a job role** from dropdown
3. **Run analysis** and verify results
4. **Check dashboard** displays correctly
5. **Test report download** functionality

### 3. Monitor Logs

#### Render
- Check Render dashboard logs
- Look for errors in build or runtime logs

#### Heroku
```bash
heroku logs --tail
```

#### Docker
```bash
docker logs ai-resume-matcher
```

## Troubleshooting Common Issues

### Issue 1: Build Fails - spaCy Model Error

**Solution**: The Dockerfile includes spaCy model download. If it fails, ensure Python version compatibility.

### Issue 2: Port Already in Use

**Solution**: The app uses PORT environment variable. Cloud platforms set this automatically.

### Issue 3: Memory Issues on Free Tier

**Solution**: 
- Set `ENABLE_EMBEDDINGS=false` in environment variables
- Reduce worker count in gunicorn config
- Use smaller model variants

### Issue 4: CORS Errors

**Solution**: The Flask app is configured to handle same-origin requests. If using custom domain, ensure proper DNS setup.

### Issue 5: Slow Performance

**Solution**:
- Use paid tier for better CPU/memory
- Enable embeddings for better semantic matching
- Optimize resume file sizes

## Security Best Practices

1. **Never commit .env file** to git
2. **Use environment variables** for sensitive data
3. **Enable HTTPS** (automatic on most platforms)
4. **Regular updates** of dependencies
5. **Monitor logs** for suspicious activity
6. **Rate limiting** for production use

## Scaling Considerations

### For High Traffic:

1. **Increase workers** in gunicorn config
2. **Use load balancer** (nginx, AWS ALB)
3. **Deploy multiple instances**
4. **Use CDN** for static assets
5. **Database integration** for persistent storage

### Cost Optimization:

1. **Start with free tiers** (Render, Railway)
2. **Monitor resource usage**
3. **Scale up only when needed**
4. **Use spot instances** on cloud providers

## Maintenance

### Regular Updates:

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Rebuild and redeploy
docker build -t ai-resume-matcher .
docker push yourusername/ai-resume-matcher:latest
```

### Backup Strategy:

- Keep git repository updated
- Export important configurations
- Document custom environment variables

## Support and Resources

- **GitHub Issues**: Report bugs in repository
- **Documentation**: Check README.md for detailed features
- **Logs**: Always check application logs first when debugging
- **Community**: Join relevant forums for deployment help

## Quick Reference Commands

```bash
# Local testing
python app.py
pytest -v

# Docker operations
docker build -t ai-resume-matcher .
docker run -p 5000:5000 ai-resume-matcher

# Git operations
git add .
git commit -m "Update"
git push origin main

# Heroku operations
heroku logs --tail
heroku config:set KEY=value

# Render operations
# Use Render dashboard for most operations
```

## Success Checklist

- [ ] All tests pass locally
- [ ] Application runs without errors locally
- [ ] Docker build succeeds
- [ ] Git repository is up to date
- [ ] Environment variables configured (if needed)
- [ ] Deployment platform is set up
- [ ] Build process completes successfully
- [ ] Application is accessible via URL
- [ ] API endpoints respond correctly
- [ ] File upload works
- [ ] Analysis functionality works
- [ ] Report generation works
- [ ] HTTPS is enabled
- [ ] Logs show no critical errors

Following this guide should ensure a smooth, error-free deployment of your AI Resume & Job Matcher application!