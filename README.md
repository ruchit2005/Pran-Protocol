# 🏥 Swastha - AI Healthcare Assistant

An intelligent healthcare support system powered by Multi-Agent RAG architecture, combining traditional Ayurvedic wisdom with modern AI technology.

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
- **Mental Wellness** - Support and resources
- **Hospital Locator** - Find nearby facilities

### 🔐 **Authentication**
- Google OAuth via Firebase
- Secure JWT tokens
- User profile management
- Session history tracking

### 🎨 **Modern UI**
- Next.js 16 + React 19 frontend
- Real-time chat interface
- Voice input support
- Text-to-speech responses
- Responsive design

## 🏗️ Project Structure

```
.
├── src/                          # Backend Python modules
│   ├── chains/                   # LangChain agents
│   │   ├── base_chains.py       # Core chains (safety, intent, fusion)
│   │   └── specialized_chains.py # Domain agents (ayurveda, yoga, etc.)
│   ├── auth/                     # Authentication
│   │   ├── firebase_auth.py     # Firebase Admin SDK
│   │   └── security.py          # JWT & password hashing
│   ├── database/                 # SQLite models
│   ├── document_processor/       # RAG document ingestion
│   ├── embeddings/               # Sentence transformers
│   ├── retrieval/                # Vector search & reranking
│   └── vector_store/             # ChromaDB management
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                 # Pages & API routes
│   │   │   ├── login/           # Login page
│   │   │   ├── signup/          # Signup page
│   │   │   └── api/             # API endpoints (proxy to backend)
│   │   ├── components/          # React components
│   │   │   └── chat.tsx         # Main chat interface
│   │   └── lib/
│   │       └── firebase.ts      # Firebase client config
│   └── next.config.ts           # Next.js configuration
├── config/                       # Configuration files
│   ├── settings.py              # Application settings
│   └── firebase-service-account.json  # (not in git)
├── data/                         # RAG data
│   ├── chroma_db/               # Vector database
│   ├── raw/                     # Source documents
│   └── processed/               # Processed documents
├── api.py                        # FastAPI backend
├── ingest.py                     # RAG ingestion script
├── cli.py                        # CLI interface
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Firebase account
- OpenAI API key

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

**Create `.env` file from example:**
```bash
cp .env.example .env
```

**Edit `.env` with your credentials:**
```env
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Tavily (for web search)
TAVILY_API_KEY=tvly-your-key-here

# YouTube Data API
YOUTUBE_API_KEY=your-youtube-key

# Firebase (from Firebase Console)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef

# Backend URL
BACKEND_URL=http://localhost:8000

# JWT Secret (generate random string)
SECRET_KEY=your-super-secret-key
```

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
uvicorn api:app --reload --host 0.0.0.0 --port 8000

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
- 🎤 Click microphone icon to speak your query
- 🔊 Click speaker icon on bot responses to hear them

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
- ChromaDB - Vector database
- SQLite - User & session storage
- Firebase Admin SDK - Authentication
- OpenAI GPT-4o-mini - LLM
- Sentence Transformers - Embeddings

**Frontend:**
- Next.js 16 - React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- Firebase Auth - Google OAuth

## 🔐 Security

- ✅ All sensitive data in `.env` (not committed to git)
- ✅ Firebase service account JSON excluded from git
- ✅ JWT token authentication
- ✅ Password hashing with bcrypt
- ✅ PII detection and filtering
- ✅ Content safety guardrails
- ✅ Emergency queries prioritized (never blocked)

### What's Protected in `.gitignore`
- `.env` (all API keys and secrets)
- `config/firebase-service-account.json`
- `healthcare.db` (user database)
- `data/chroma_db/` (vector database)
- `audio_cache/`, `logs/`
- `node_modules/`, `__pycache__/`

## 📚 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints
- `POST /auth/signup` - Create account
- `POST /auth/login` - Password login
- `POST /auth/firebase-login` - Google OAuth
- `GET /auth/me` - Get user profile
- `POST /chat` - Send message
- `GET /sessions` - List chat sessions
- `POST /tts` - Text-to-speech

## 🛠️ Development

### Project Commands

```bash
# Backend
uvicorn api:app --reload              # Start with auto-reload
python cli.py                         # CLI interface
python ingest.py                      # Ingest documents
python check_db.py                    # Inspect database

# Frontend
cd frontend
npm run dev                           # Development server
npm run build                         # Production build
npm run start                         # Production server
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

**Users Table:**
- `id`, `email`, `hashed_password`
- `firebase_uid`, `display_name`, `photo_url`
- `created_at`

**Sessions Table:**
- `id`, `user_id`, `title`, `created_at`

**Messages Table:**
- `id`, `session_id`, `role`, `content`, `timestamp`

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
1. Check `FIREBASE_SETUP.md` for Firebase configuration
2. Check `SECURITY.md` for security guidelines
3. See API docs at `/docs` when backend is running
4. Open an issue on GitHub

---

**Made with 🌿 for holistic healthcare**
