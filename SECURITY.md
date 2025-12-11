# 🔒 Security & Setup Instructions

## ⚠️ IMPORTANT - Files You Need to Create

After cloning this repository, you need to create these files with your own credentials:

### 1. Backend Environment Variables
**File:** `Pran-Protocol/.env`

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:
- OpenAI API Key
- Tavily API Key
- YouTube API Key

### 2. Frontend Environment Variables
**File:** `Pran-Protocol/frontend/.env.local`

```bash
cd frontend
cp .env.local.example .env.local
```

Then edit `.env.local` and add your Firebase configuration.

### 3. Firebase Service Account
**File:** `Pran-Protocol/config/firebase-service-account.json`

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to Project Settings > Service Accounts
4. Click "Generate new private key"
5. Save the JSON file as `config/firebase-service-account.json`

### 4. Create Database
The SQLite database will be created automatically when you first run the backend.

---

## 📋 Setup Checklist

- [ ] Copy `.env.example` to `.env` and add API keys
- [ ] Copy `frontend/.env.local.example` to `frontend/.env.local` and add Firebase config
- [ ] Download Firebase service account JSON to `config/firebase-service-account.json`
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Install frontend dependencies: `cd frontend && npm install`
- [ ] Run backend: `uvicorn api:app --reload --host 0.0.0.0 --port 8000`
- [ ] Run frontend: `cd frontend && npm run dev`

---

## 🚨 NEVER COMMIT THESE FILES:
- `.env`
- `frontend/.env.local`
- `config/firebase-service-account.json`
- `config/credentials.json`
- `healthcare.db`
- Any file with API keys or secrets

These are already in `.gitignore` for your protection!
