# Quick Start Deployment Guide

## Fastest Deployment Options

### Option 1: Render.com (Easiest - Free Tier)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Select "Docker" runtime
   - Click "Create Web Service"

3. **Done!** Your app will be live in 5-10 minutes.

### Option 2: Local Docker (Testing)

**Windows:**
```bash
deploy-local.bat
```

**Mac/Linux:**
```bash
chmod +x deploy-local.sh
./deploy-local.sh
```

Access at: `http://localhost:5000`

### Option 3: Railway (Simple)

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Click "Deploy"

## Pre-Deployment Checklist

- [ ] Run `pytest -v` - all tests pass
- [ ] Run `python app.py` - app works locally
- [ ] Updated requirements.txt with compatible versions
- [ ] Dockerfile is present and updated
- [ ] Procfile is present
- [ ] .env.example is present
- [ ] No .env file committed to git

## Environment Variables (Optional)

Only needed if you want AI features:

```bash
OPENAI_API_KEY=your_key_here
ENABLE_EMBEDDINGS=false
```

## Post-Deployment Test

```bash
curl https://your-app-url.com/api/roles
```

Should return JSON with job roles.

## Common Issues

**Build fails?** Check Python version in Dockerfile (currently 3.12)

**Port errors?** Cloud platforms set PORT automatically

**Memory issues?** Set `ENABLE_EMBEDDINGS=false`

## Need Help?

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide.