# 🚨 IMPORTANT: Required Files Checklist

Before running the project, make sure you have these files configured:

## ✅ Backend (.env file)
1. Copy `.env.example` to `.env`
2. Fill in ALL values:
   - `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
   - `TAVILY_API_KEY` - Get from https://tavily.com
   - `YOUTUBE_API_KEY` - Get from Google Cloud Console
   - `MONGODB_URI` - Your MongoDB Atlas connection string
   - `MASTER_ENCRYPTION_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Firebase credentials (from Firebase Console)

## ✅ Firebase Service Account
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key"
3. Save the JSON file as `config/firebase-service-account.json`
4. **NEVER commit this file to Git!**

## ✅ Frontend (.env.local file)
1. Copy `frontend/.env.local.example` to `frontend/.env.local`
2. Fill in Firebase web app credentials from Firebase Console

## ✅ Code Files (These SHOULD be in Git)
These files contain NO secrets and should always be committed:
- `frontend/src/lib/firebase.ts` - Firebase client config
- `src/auth/firebase_auth.py` - Firebase auth logic
- All other `.py`, `.ts`, `.tsx` files

## 🔒 Files That Should NEVER Be Committed
- `.env` - Backend secrets
- `frontend/.env.local` - Frontend secrets
- `config/firebase-service-account.json` - Firebase admin credentials
- `*.db`, `*.sqlite` - Database files
- `__pycache__/`, `node_modules/` - Generated files

## ⚠️ Common Setup Issues

### Issue: "firebase.ts not found"
**Solution:** This file SHOULD be in Git. If missing, someone accidentally added it to `.gitignore`. It's now explicitly allowed in `.gitignore`.

### Issue: "Firebase not initialized"
**Solution:** Missing `config/firebase-service-account.json`. Download from Firebase Console.

### Issue: "MongoDB connection failed"
**Solution:** 
1. Check MongoDB URI in `.env`
2. Whitelist your IP in MongoDB Atlas: Network Access → Add IP Address

### Issue: "Module not found" errors
**Solution:**
```bash
# Backend
cd Pran-Protocol
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## 📦 Installation Steps

### 1. Clone Repository
```bash
git clone <repository-url>
cd Pran-Protocol
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your values

# Add Firebase service account JSON
# Download from Firebase Console and save as:
# config/firebase-service-account.json
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
copy .env.local.example .env.local
# Edit .env.local with your Firebase web credentials
```

### 4. Run Project
```bash
# Terminal 1 - Backend
cd Pran-Protocol
venv\Scripts\activate
python api_mongodb.py

# Terminal 2 - Frontend
cd Pran-Protocol/frontend
npm run dev
```

### 5. Access Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔑 Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy to `.env` as `OPENAI_API_KEY`

### Tavily
1. Go to https://tavily.com
2. Sign up and get API key
3. Copy to `.env` as `TAVILY_API_KEY`

### YouTube
1. Go to https://console.cloud.google.com
2. Enable YouTube Data API v3
3. Create credentials → API key
4. Copy to `.env` as `YOUTUBE_API_KEY`

### MongoDB
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create cluster
3. Get connection string
4. Replace `<password>` and add database name
5. Whitelist your IP address

### Firebase
1. Go to https://console.firebase.google.com
2. Create project (or use existing)
3. Enable Authentication → Google Sign-In
4. Get web app config (for frontend `.env.local`)
5. Download service account JSON (for backend `config/firebase-service-account.json`)

## 📞 Need Help?
If you're still stuck, check:
1. All `.env` files are properly filled
2. Virtual environment is activated (`venv\Scripts\activate`)
3. Both backend and frontend servers are running
4. No port conflicts (8000 for backend, 3000 for frontend)
