# Pran-Protocol Setup Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- Firebase project
- OpenAI API key

## Backend Setup

1. **Install Python dependencies**
   ```bash
   cd Pran-Protocol
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Fill in all required values:
     - OpenAI API key
     - MongoDB URI
     - Firebase credentials
     - Generate encryption key: `python -c "import secrets; print(secrets.token_hex(32))"`

3. **Add Firebase service account**
   - Download service account JSON from Firebase Console
   - Save as `config/firebase-service-account.json`
   - **NEVER commit this file to Git**

4. **Run backend**
   ```bash
   python api_mongodb.py
   ```
   Backend will run on `http://localhost:8000`

## Frontend Setup

1. **Install Node dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment variables**
   - Copy `.env.local.example` to `.env.local`
   - Fill in Firebase web app credentials (from Firebase Console)

3. **Run frontend**
   ```bash
   npm run dev
   ```
   Frontend will run on `http://localhost:3000`

## Important Files (DO NOT COMMIT)
- `.env` - Backend secrets
- `frontend/.env.local` - Frontend secrets
- `config/firebase-service-account.json` - Firebase admin SDK credentials

## Troubleshooting

### "Module not found" errors
- Make sure you've activated the virtual environment
- Run `pip install -r requirements.txt` again

### "Firebase not initialized"
- Check that `config/firebase-service-account.json` exists
- Verify Firebase credentials in `.env`

### "MongoDB connection failed"
- Check MongoDB URI format in `.env`
- Ensure IP address is whitelisted in MongoDB Atlas

### "API 404 errors"
- Make sure backend is running on port 8000
- Check CORS settings in `api_mongodb.py`
