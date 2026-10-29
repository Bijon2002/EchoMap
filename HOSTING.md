# 🚀 Hosting EchoMap (Production Guide)

EchoMap can be hosted for **free** on multiple cloud platforms within 2-5 minutes.

---

## Option 1: Render.com (Recommended — 1-Click Free Hosting)

1. Fork or push the `EchoMap` repository to your **GitHub** account.
2. Sign up at [Render.com](https://render.com) (free).
3. Click **"New +"** &rarr; **"Web Service"**.
4. Select your `EchoMap` GitHub repository.
5. Configure the following:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
6. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: Your Gemini API key (`AQ.Ab8RN...`)
   - `GEMINI_MODEL`: `gemini-3.5-flash`
7. Click **Create Web Service**. Your app will be live at `https://your-app.onrender.com`.

---

## Option 2: Railway.app (Fastest Deployment)

1. Go to [Railway.app](https://railway.app).
2. Click **"New Project"** &rarr; **"Deploy from GitHub repo"**.
3. Select `EchoMap`.
4. Railway will automatically detect the `Dockerfile` and `Procfile`.
5. In **Variables**, add `GEMINI_API_KEY`.
6. Click **Deploy**.

---

## Option 3: Hugging Face Spaces (Free Cloud Docker)

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces).
2. Click **Create new Space**.
3. Select **Space SDK**: **Docker** &rarr; **Blank**.
4. Clone your space repo and push all `EchoMap` files into it.
5. In Space Settings &rarr; **Variables and secrets**, add `GEMINI_API_KEY`.
6. Your space will build and launch automatically.

---

## Option 4: Local or VPS (Ubuntu / Debian / Windows)

```bash
# Clone and enter directory
cd EchoMap

# Install dependencies
pip install -r requirements.txt

# Run production server
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Then open `http://localhost:8000`.

