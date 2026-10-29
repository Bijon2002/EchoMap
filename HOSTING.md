# EchoMap Free Hosting Guide

EchoMap is fully configured for zero-cost cloud hosting on **Render**, **Railway**, **Koyeb**, or **Hugging Face Spaces**.

---

## Option 1: Render.com (Recommended Free Tier)

1. Push this repository to **GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial EchoMap release with Nexus AI"
   git remote add origin https://github.com/<your-username>/echomap.git
   git push -u origin main
   ```
2. Log into [Render Dashboard](https://dashboard.render.com/) and click **New → Web Service**.
3. Connect your `echomap` GitHub repository.
4. Render will automatically detect [`render.yaml`](file:///a:/EchoMap/render.yaml):
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `NEXUS_API_KEY`: `sk-YRxt1RzLVFoFqmnwZpSIFA`
   - `NEXUS_BASE_URL`: `https://nexusapi.navigatelabs.ai`
   - `NEXUS_MODEL`: `gemini-3.1-flash-lite`
6. Click **Create Web Service**. Within ~2 minutes, your public HTTPS app URL will be live!

---

## Option 2: Railway.app

1. Go to [railway.app](https://railway.app/) → **New Project → Deploy from GitHub repo**.
2. Select your repository. Railway automatically reads the [`Procfile`](file:///a:/EchoMap/Procfile) and [`requirements.txt`](file:///a:/EchoMap/requirements.txt).
3. In the project **Variables** tab, add:
   - `NEXUS_API_KEY`: your Nexus key
   - `NEXUS_BASE_URL`: `https://nexusapi.navigatelabs.ai`
   - `NEXUS_MODEL`: `gemini-3.1-flash-lite`
4. In **Settings → Networking**, click **Generate Domain** to get a public URL.

---

## Option 3: Docker Deployment (Koyeb, Fly.io, Self-Hosted)

Run with the pre-built [`Dockerfile`](file:///a:/EchoMap/Dockerfile):

```bash
docker build -t echomap .
docker run -p 8000:8000 \
  -e NEXUS_API_KEY="sk-YRxt1RzLVFoFqmnwZpSIFA" \
  -e NEXUS_BASE_URL="https://nexusapi.navigatelabs.ai" \
  -e NEXUS_MODEL="gemini-3.1-flash-lite" \
  echomap
```

---

## Production Security Notes

- The `.gitignore` prevents your real [`.env`](file:///a:/EchoMap/.env) and `echomap.db` from ever being pushed to public GitHub.
- Users can still override or configure their own API keys via the **Settings (⚙️)** UI in the hosted web app.
