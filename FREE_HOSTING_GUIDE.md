# Free Hosting Guide for FastAPI + Jinja2 Admin Panel

## Why Jinja2 is Perfect for Free Hosting

✅ **Single Deployment**: Backend + Admin Panel = One FastAPI app  
✅ **No Build Process**: No npm, webpack, or separate frontend  
✅ **Simple Static Files**: Templates served directly from FastAPI  
✅ **Low Resource Usage**: No Node.js process needed  
✅ **Works on All Free Tiers**: Render, Railway, Fly.io, PythonAnywhere  

---

## Recommended: Render.com (Easiest)

### Setup Steps:

1. **Create `render.yaml`** (for easy deployment):
```yaml
services:
  - type: web
    name: sokoni-africa-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: ALLOWED_ORIGINS
        value: https://your-app.onrender.com
    healthCheckPath: /docs

databases:
  - name: sokoni-africa-db
    databaseName: sokoni_africa
    user: sokoni_user
```

2. **Update `requirements.txt`** (add Jinja2):
```
jinja2==3.1.2
aiofiles==23.2.1
```

3. **Update `main.py`** to serve templates:
```python
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Templates directory
templates = Jinja2Templates(directory="templates")

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})
```

4. **Deploy to Render**:
   - Push code to GitHub
   - Connect GitHub repo to Render
   - Render auto-detects Python and deploys
   - Add PostgreSQL database (free tier)
   - Set environment variables
   - Done! 🎉

### Render.com Free Tier:
- ✅ 750 hours/month (enough for 24/7)
- ✅ Free PostgreSQL database
- ✅ Auto-deploy from GitHub
- ✅ Custom domain support
- ✅ HTTPS included

---

## Alternative: Railway.app

### Setup:

1. **Create `Procfile`**:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

2. **Create `railway.json`**:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

3. **Deploy**:
   - Install Railway CLI: `npm i -g @railway/cli`
   - Run: `railway login` → `railway init` → `railway up`
   - Or use Railway web dashboard

### Railway Free Tier:
- ✅ $5 credit/month
- ✅ Free PostgreSQL
- ✅ Simple deployment

---

## Alternative: Fly.io

### Setup:

1. **Install Fly CLI**:
```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
```

2. **Create `fly.toml`**:
```toml
app = "sokoni-africa-backend"
primary_region = "iad"

[build]

[env]
  PORT = "8080"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

3. **Deploy**:
```bash
fly launch
fly deploy
```

### Fly.io Free Tier:
- ✅ 3 shared VMs
- ✅ Free PostgreSQL
- ✅ Global deployment

---

## Project Structure for Hosting

```
africa_sokoni_app_backend/
├── main.py                 # FastAPI app (includes admin routes)
├── requirements.txt        # Dependencies
├── render.yaml            # Render.com config (optional)
├── Procfile              # Railway config (optional)
├── fly.toml              # Fly.io config (optional)
├── templates/             # Jinja2 templates
│   └── admin/
│       ├── base.html
│       ├── dashboard.html
│       ├── users.html
│       └── products.html
├── static/               # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── images/
└── app/
    └── routers/          # Your existing API routes
```

---

## Environment Variables for Production

Create these in your hosting platform:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=https://your-app.onrender.com,https://admin.your-app.onrender.com
ENVIRONMENT=production
DEBUG=False
```

---

## Quick Comparison

| Platform | Free Tier | Ease of Use | Best For |
|----------|-----------|-------------|----------|
| **Render.com** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **Recommended** |
| Railway.app | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Good alternative |
| Fly.io | ⭐⭐⭐ | ⭐⭐⭐ | Global deployment |
| PythonAnywhere | ⭐⭐ | ⭐⭐⭐⭐ | Simple Python apps |

---

## Why NOT Separate Frontend (React/Vue)?

❌ **Two deployments needed** (backend + frontend)  
❌ **Build process required** (npm build, webpack)  
❌ **More complex** (CORS, API calls, routing)  
❌ **Higher resource usage** (Node.js + Python)  
❌ **Harder to deploy** (two services to manage)  

✅ **Jinja2 = One deployment, simple, free-friendly!**

---

## Next Steps

1. ✅ I'll create the Jinja2 admin panel structure
2. ✅ Add hosting configuration files
3. ✅ Make it production-ready
4. ✅ You deploy to Render.com (or your choice)

Ready to create the admin panel? 🚀

