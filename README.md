# 🏥 Pran Protocol - AI Healthcare Assistant

A HIPAA-compliant, enterprise-grade healthcare support system powered by Multi-Agent RAG architecture, blockchain audit logging, and secure cloud infrastructure. Combines traditional Ayurvedic wisdom with modern AI technology.

## ✨ Features

### 🤖 **Multi-Agent Architecture**
- **Safety Guardrails** - Content filtering and PII protection
- **Intent Classification** - Smart routing to specialized agents
- **Symptom Checker** - Emergency detection with hospital routing
- **RAG-Powered Recommendations**:
  - 🌿 Ayurvedic remedies from curated knowledge base
  - 🧘 Yoga therapy with video recommendations
  - 💡 Wellness guidance
- **Government Schemes** - Health insurance and benefits search
- **Mental Wellness** - Support and resources with Sarvam AI Hindi TTS
- **Hospital Locator** - Find nearby facilities using Mapbox
- **Voice Features** - Speech-to-text (OpenAI Whisper) and multilingual TTS

### 🔐 **Security & Compliance**
- **Firebase Authentication** - Google OAuth & JWT tokens
- **End-to-End Encryption** - AES-256-GCM for PHI data
- **Blockchain Audit Logging** - PostgreSQL-based immutable audit trail
- **DISHA Compliance** - India's Digital Information Security in Healthcare Act
- **Consent Management** - Explicit user consent tracking
- **Session Management** - Secure session history with MongoDB

### 🎨 **Modern UI**
- Next.js 15 + React 19 frontend
- Real-time chat interface with i18n support (English/Hindi)
- Voice input support with language detection
- Text-to-speech responses (OpenAI + Sarvam AI for Hindi)
- Responsive design with Tailwind CSS
- Document upload and processing

## 🏗️ Project Structure

```
.
├── src/                          # Backend Python modules
│   ├── chains/                   # LangChain agents
│   │   ├── base_chains.py       # Core chains (safety, intent, fusion)
│   │   ├── specialized_chains.py # Domain agents (ayurveda, yoga, etc.)
│   │   ├── health_advisory_chain.py
│   │   ├── medical_reasoning_chain.py
│   │   ├── profile_chain.py
│   │   └── document_qa_chain.py
│   ├── auth/                     # Authentication
│   │   ├── firebase_auth.py     # Firebase Admin SDK
│   │   ├── security.py          # JWT & password hashing
│   │   └── deps.py              # Auth dependencies
│   ├── database/                 # Database layer
│   │   ├── mongodb_manager.py   # MongoDB connection
│   │   ├── mongodb_models.py    # Pydantic models
│   │   ├── models.py            # SQLAlchemy models (legacy)
│   │   └── core.py              # Database core
│   ├── blockchain/               # Blockchain audit logging
│   │   ├── postgres_blockchain.py  # Cloud PostgreSQL blockchain
│   │   ├── private_blockchain.py   # Local SQLite blockchain
│   │   ├── audit_logger.py
│   │   └── ledger.py
│   ├── security/                 # Security & encryption
│   │   └── encryption.py        # AES-256-GCM PHI encryption
│   ├── compliance/               # Healthcare compliance
│   │   └── disha_compliance.py  # DISHA compliance manager
│   ├── document_processor/       # RAG document ingestion
│   │   ├── chunker.py
│   │   ├── enrichment_manager.py
│   │   └── pdf_processor.py
│   ├── embeddings/               # Sentence transformers
│   ├── retrieval/                # Vector search & reranking
│   └── vector_store/             # Pinecone/ChromaDB management
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                 # Pages & API routes
│   │   │   ├── [locale]/        # i18n routing (en/hi)
│   │   │   └── api/             # API endpoints (proxy)
│   │   ├── components/          # React components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── VoiceRecorder.tsx
│   │   │   └── DocumentUpload.tsx
│   │   ├── lib/
│   │   │   └── firebase.ts      # Firebase client config
│   │   └── i18n/                # Internationalization
│   └── messages/                # Translation files (en.json, hi.json)
├── config/                       # Configuration files
│   ├── settings.py              # Application settings
│   └── firebase-service-account.json  # (not in git)
├── data/                         # RAG data
│   ├── chroma_db/               # Local vector database
│   ├── raw/                     # Source documents
│   └── processed/               # Processed documents
├── api_mongodb.py                # FastAPI backend (MongoDB-based)
├── ingest.py                     # RAG ingestion script
├── cli.py                        # CLI interface
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Firebase account
- OpenAI API keys (2 for load balancing)
- MongoDB Atlas account
- Pinecone account (for cloud vector store)
- Supabase PostgreSQL database (for blockchain)
- Tavily API key (for web search)
- YouTube Data API key
- Mapbox API key (for location services)
- Sarvam AI API key (for Hindi TTS)

### 1. Clone & Install

```bash
# Clone repository
git clone <your-repo-url>
cd Pran-Protocol

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Environment Setup

**⚠️ IMPORTANT: Create `.env` file BEFORE running the application!**

**Create `.env` file from example:**
```bash
cp .env.example .env
```

**Edit `.env` with your credentials:**
```env
# === OpenAI API Keys (Load Balanced) ===
OPENAI_API_KEY_1=sk-proj-your-primary-key
OPENAI_API_KEY_2=sk-proj-your-secondary-key

# === Tavily API Key ===
TAVILY_API_KEY=tvly-dev-your-key

# === YouTube API Key ===
YOUTUBE_API_KEY=your-youtube-key
YOUTUBE_SEARCH_MAX_RESULTS=3
VIDEO_CACHE_TTL_SECONDS=900

# === Mapbox API Key ===
MAPBOX_API_KEY=your-mapbox-key

# === Sarvam AI (Hindi TTS) ===
SARVAM_API_KEY=sk_your-sarvam-key

# Firebase Configuration (Shared between Frontend and Backend)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef
FIREBASE_SERVICE_ACCOUNT_PATH=config/firebase-service-account.json

# Backend URL
BACKEND_URL=http://localhost:8000

# JWT Authentication Secret
SECRET_KEY=your-super-secret-key-generate-with-secrets

# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_DB_NAME=pran-protocol

# Encryption Key for PHI Data (DO NOT LOSE THIS!)
MASTER_ENCRYPTION_KEY=generate-64-char-hex-key

# Vector Store Configuration
VECTOR_STORE_TYPE=pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=pran-protocol

# Blockchain Configuration (PostgreSQL on Supabase)
BLOCKCHAIN_TYPE=private
BLOCKCHAIN_DATABASE_URL=postgresql://user:pass@host:5432/postgres

# News API (Optional)
NEWS_API_KEY=your-news-api-key
```

**❌ Common Error**: If you see "Cannot read properties of undefined (reading 'app')" in the frontend, it means your `.env` file is missing or incomplete. Make sure ALL Firebase variables are filled in.

### 3. Firebase Setup

**Download Service Account Key:**
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate new private key**
5. Save as `config/firebase-service-account.json`

**Enable Google Sign-In:**
1. Go to **Authentication** → **Sign-in method**
2. Enable **Google** provider
3. Add your domain (localhost for development)

**Detailed setup guide:** See `FIREBASE_SETUP.md`

### 4. Run the Application

```bash
# Terminal 1: Start Backend (from root directory)
uvicorn api_mongodb:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend (from root directory)
cd frontend
npm run dev
```

**Access the app:** Open [http://localhost:3000](http://localhost:3000)

### 5. (Optional) Ingest Custom Documents

Add your own Ayurveda/Yoga documents to enhance the knowledge base:

```bash
# Place documents in data/raw/
# Then run ingestion:
python ingest.py
```

## 📖 Usage

### Web Interface

1. **Sign Up / Login** with Google
2. **Start chatting** with the healthcare assistant
3. **Ask questions** about:
   - Ayurvedic remedies
   - Yoga poses and exercises
   - Symptoms and health concerns
   - Government health schemes
   - Mental wellness support

### Voice Features
- 🎤 Click microphone icon to speak your query (supports English/Hindi)
- 🔊 Click speaker icon on bot responses to hear them
- 🌐 Hindi TTS powered by Sarvam AI
- 📝 English TTS powered by OpenAI

### Document Upload
- 📄 Upload medical documents, reports, and prescriptions
- 🔍 RAG-powered document Q&A
- 🔐 Encrypted storage and secure processing

### Example Queries

```
"I have a backache for 2 days"
"What yoga poses help with anxiety?"
"Remedies for migraine?"
"Government health schemes in India"
"Meditation techniques for better sleep"
```

## 🏗️ Architecture

### Multi-Agent Workflow

```
User Query
    ↓
🛡️ Safety Guardrail (PII & Content Filter)
    ↓
🎯 Intent Classification (8 specialized agents)
    ↓
📊 Route to Agent
    ↓
┌──────────────────────────┐
│ Symptom Checker          │ → Multi-Agent Response:
│                          │   ├─ Emergency? → Hospital Locator
│                          │   └─ Non-Emergency:
│                          │      ├─ 🌿 Ayurveda Agent (RAG)
│                          │      ├─ 🧘 Yoga Agent (RAG + YouTube)
│                          │      └─ 💡 Wellness Agent
├──────────────────────────┤
│ Government Schemes       │ → Web Search + Recommendations
│ Mental Wellness          │ → Support + Yoga Videos
│ AYUSH Support            │ → Traditional Medicine (RAG)
│ Hospital Locator         │ → Find Facilities
│ Yoga Therapy             │ → Poses + Videos (RAG + YouTube)
│ Ayurveda                 │ → Remedies (RAG)
│ General Wellness         │ → Guidance (RAG)
└──────────────────────────┘
    ↓
🔗 Response Fusion (Combines multi-agent outputs)
    ↓
📤 Formatted Response to User
```

### Tech Stack

**Backend:**
- FastAPI - REST API
- LangChain - Agent orchestration
- Pinecone - Cloud vector database
- ChromaDB - Local vector database (fallback)
- MongoDB Atlas - User, session & message storage
- PostgreSQL (Supabase) - Blockchain audit logging
- Firebase Admin SDK - Authentication
- OpenAI GPT-4o-mini - LLM
- OpenAI Whisper - Speech-to-text
- Sentence Transformers - Embeddings
- AES-256-GCM - PHI encryption

**Frontend:**
- Next.js 15 - React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- Firebase Auth - Google OAuth
- next-intl - i18n support (English/Hindi)

**Cloud Services:**
- Firebase - Authentication & storage
- MongoDB Atlas - NoSQL database
- Supabase - PostgreSQL blockchain
- Pinecone - Vector database
- Mapbox - Location services
- Sarvam AI - Hindi text-to-speech

## 🔐 Security

- ✅ All sensitive data in `.env` (not committed to git)
- ✅ Firebase service account JSON excluded from git
- ✅ JWT token authentication with secure rotation
- ✅ AES-256-GCM encryption for PHI (Protected Health Information)
- ✅ Master encryption key management
- ✅ PII detection and filtering
- ✅ Content safety guardrails
- ✅ Emergency queries prioritized (never blocked)
- ✅ DISHA compliance for Indian healthcare regulations
- ✅ Blockchain audit trail (immutable logging)
- ✅ Consent management with version tracking
- ✅ Session security with MongoDB

### HIPAA Compliance Features
- **Encryption at Rest**: All PHI encrypted with AES-256-GCM
- **Encryption in Transit**: HTTPS/TLS for all API calls
- **Audit Logging**: Immutable blockchain-based audit trail
- **Access Controls**: Role-based authentication with Firebase
- **Consent Management**: Explicit user consent tracking
- **Data Integrity**: PostgreSQL blockchain ensures data immutability

### What's Protected in `.gitignore`
- `.env` (all API keys and secrets)
- `config/firebase-service-account.json`
- `healthcare.db` (legacy user database)
- `data/chroma_db/` (local vector database)
- `data/blockchain.db` (local blockchain database)
- `audio_cache/`, `logs/`, `uploads/`
- `node_modules/`, `__pycache__/`, `.next/`
- `audit_ledger.json`

## 📚 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints
- `POST /auth/signup` - Create account (deprecated)
- `POST /auth/login` - Password login (deprecated)
- `POST /auth/firebase-login` - Google OAuth (primary)
- `GET /auth/me` - Get user profile
- `POST /chat` - Send message
- `GET /sessions` - List chat sessions
- `GET /sessions/{session_id}/messages` - Get session messages
- `POST /tts` - Text-to-speech (OpenAI)
- `POST /tts/sarvam` - Hindi text-to-speech (Sarvam AI)
- `POST /transcribe` - Speech-to-text (OpenAI Whisper)
- `POST /upload-document` - Upload medical documents
- `POST /consent/accept` - Accept consent agreement
- `GET /audit/user` - Get user audit logs (blockchain)
- `POST /nearby-places` - Find nearby hospitals (Mapbox)

## 🛠️ Development

### Project Commands

```bash
# Backend
uvicorn api_mongodb:app --reload        # Start with auto-reload
python cli.py                           # CLI interface
python ingest.py                        # Ingest documents
python check_profile.py                 # Check user profiles
python clear_databases.py               # Clear all databases (dev only)
python migrate_to_cloud_vectorstore.py  # Migrate to Pinecone

# Frontend
cd frontend
npm run dev                             # Development server
npm run build                           # Production build
npm run start                           # Production server
npm run lint                            # Run ESLint
```

### Adding New Agents

1. **Create chain class** in `src/chains/specialized_chains.py`:
```python
class MyNewChain(BaseChain):
    def invoke(self, inputs: dict) -> dict:
        # Your logic here
        return {"output": "response"}
```

2. **Initialize in workflow** (`src/workflow.py`):
```python
self.my_chain = MyNewChain(config)
```

3. **Add routing logic** in `run()` method

### RAG Document Ingestion

Add documents to `data/raw/` then run:
```bash
python ingest.py
```

Supported formats: `.txt`, `.pdf`, `.docx`, `.md`

### Database Schema

**MongoDB Collections:**

**users:**
- `_id`, `email`, `firebase_uid`
- `display_name`, `photo_url`
- `created_at`, `last_login`
- `profile` (encrypted PHI data)
- `consent_agreements` (DISHA compliance)

**sessions:**
- `_id`, `user_id`, `title`
- `created_at`, `updated_at`
- `message_count`

**messages:**
- `_id`, `session_id`, `user_id`
- `role` (user/assistant), `content` (encrypted)
- `timestamp`, `metadata`

**audit_logs:**
- `_id`, `user_id`, `action`, `resource`
- `timestamp`, `ip_address`, `user_agent`
- `blockchain_hash` (reference to blockchain entry)

**PostgreSQL Blockchain:**
- Immutable audit trail
- Hash-chained blocks
- Tamper-evident logging
- HIPAA compliance

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Ayurvedic knowledge base curated from traditional texts
- Yoga therapy based on authentic practices
- Built with LangChain, OpenAI, and Firebase
- UI inspired by traditional Indian aesthetics

## 📞 Support

For setup help or issues:
1. Check `.env.example` for required environment variables
2. Ensure Firebase service account JSON is properly configured
3. Verify MongoDB Atlas connection string
4. Check Pinecone API key and index configuration
5. See API docs at `/docs` when backend is running
6. Check logs in `logs/` directory
7. Open an issue on GitHub

### Common Issues

**MongoDB Connection Failed:**
- Verify `MONGODB_URI` in `.env`
- Ensure IP whitelist in MongoDB Atlas includes your IP
- Check network connectivity

**Pinecone Index Not Found:**
- Create index with dimension 384 (for sentence-transformers)
- Verify `PINECONE_INDEX_NAME` matches your index

**Firebase Authentication Error:**
- Ensure `firebase-service-account.json` is in `config/`
- Verify all Firebase env variables are set

**Blockchain Logging Failed:**
- Check `BLOCKCHAIN_DATABASE_URL` connection
- Verify PostgreSQL database is accessible
- Falls back to local SQLite if cloud fails

---

**Made with 🌿 for holistic healthcare | HIPAA Compliant | DISHA Certified**
