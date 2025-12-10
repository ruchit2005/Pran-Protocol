# api.py — FINAL CLEAN WORKING VERSION

import logging
import tempfile
import os
from uuid import uuid4
from typing import List, Dict, Any, Optional
from datetime import timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session

# Internal modules
from src.config import HealthcareConfig
from src.workflow import HealthcareWorkflow
from src.database.core import engine, Base, get_db
from src.database.models import User, ChatSession, ChatMessage as DBChatMessage
from src.auth.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.auth.deps import get_current_user
from src.blockchain.ledger import audit_ledger

# Create DB tables
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------
# FASTAPI APP SETUP
# -------------------------------------------------------
app = FastAPI(title="Healthcare RAG Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# GLOBALS
# -------------------------------------------------------
workflow: HealthcareWorkflow | None = None
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Single audio folder for TTS
AUDIO_DIR = os.path.join(os.getcwd(), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)


# -------------------------------------------------------
# INIT WORKFLOW ON STARTUP
# -------------------------------------------------------
@app.on_event("startup")
def load_workflow():
    global workflow
    logging.info("Initializing Healthcare workflow...")

    try:
        config = HealthcareConfig()
        workflow = HealthcareWorkflow(config)
        logging.info("Workflow initialized successfully.")
    except Exception as e:
        logging.error(f"Workflow initialization failed: {e}", exc_info=True)
        workflow = None


# -------------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------------
class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatMessage(BaseModel):
    query: str
    session_id: Optional[int] = None
    generate_audio: bool = False

class SessionCreate(BaseModel):
    title: str

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str

# -------------------------------------------------------
# AUTH ENDPOINTS
# -------------------------------------------------------
@app.post("/auth/signup", response_model=Token)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Audit Log
    audit_ledger.add_block(new_user.id, "SIGNUP", "User registered")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Audit Log
    audit_ledger.add_block(user.id, "LOGIN", "User logged in")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------------------------------------------
# SESSION ENDPOINTS
# -------------------------------------------------------
@app.post("/sessions", response_model=SessionResponse)
def create_session(session: SessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_session = ChatSession(user_id=current_user.id, title=session.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    # Audit Log
    audit_ledger.add_block(current_user.id, "CREATE_SESSION", f"Created session {new_session.id}")
    
    return {
        "id": new_session.id,
        "title": new_session.title,
        "created_at": str(new_session.created_at)
    }

@app.get("/sessions", response_model=List[SessionResponse])
def get_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    return [
        {"id": s.id, "title": s.title, "created_at": str(s.created_at)}
        for s in sessions
    ]

@app.get("/sessions/{session_id}/history")
def get_session_history(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(DBChatMessage).filter(DBChatMessage.session_id == session_id).order_by(DBChatMessage.timestamp).all()
    return [
        {"role": m.role, "content": m.content, "timestamp": str(m.timestamp)}
        for m in messages
    ]

# -------------------------------------------------------
# CHAT ENDPOINT (Protected)
# -------------------------------------------------------
@app.post("/chat", response_model=Dict[str, Any])
async def handle_chat(
    message: ChatMessage, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized.")

    logging.info(f"Received query: {message.query} from user {current_user.email}")

    # Ensure session exists or create default
    session_id = message.session_id
    if not session_id:
        # Create a new session if none provided
        new_session = ChatSession(user_id=current_user.id, title=message.query[:30])
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id

    # Verify session ownership
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=403, detail="Invalid session")

    # Save User Message
    user_msg = DBChatMessage(session_id=session_id, role="user", content=message.query)
    db.add(user_msg)
    db.commit()

    # Build history context from DB
    history_msgs = db.query(DBChatMessage).filter(DBChatMessage.session_id == session_id).order_by(DBChatMessage.timestamp).all()
    history_context = ""
    if history_msgs:
        history_context += "\n\nPrevious conversation:\n"
        for i, msg in enumerate(history_msgs[-5:], 1):
             history_context += f"{i}. {msg.role.capitalize()}: {msg.content}\n"

    try:
        # Audit Log
        audit_ledger.add_block(current_user.id, "CHAT_QUERY", "User sent a message")

        result = await workflow.run(
            user_input=message.query,
            query_for_classification=message.query + history_context
        )
        
        # Generate Audio if requested
        audio_url = None
        if message.generate_audio:
             # Get the assistant output (string-safe)
            raw_output = result.get("output") if isinstance(result, dict) else result
            tts_input = raw_output if isinstance(raw_output, str) else str(raw_output)
            
            # Generate TTS
            
            # Create a simple hash of the text for caching
            import hashlib
            text_hash = hashlib.md5(tts_input.encode("utf-8")).hexdigest()
            filename = f"{text_hash}.mp3"
            tts_path = os.path.join(AUDIO_DIR, filename)
            
            # Check cache first
            if not os.path.exists(tts_path):
                logging.info(f"Generating TTS for session {session_id}. Input length: {len(tts_input)}")
                try:
                    speech = client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=tts_input[:4096], # Limit for safety
                        response_format="mp3"
                    )
                    with open(tts_path, "wb") as f:
                        f.write(speech.read())
                    logging.info(f"TTS generated successfully: {filename}")
                except Exception as e:
                    logging.error(f"TTS generation failed: {e}", exc_info=True)
                    # Don't try to continue if generation failed
                    raise e
            else:
                logging.info(f"TTS Cache Hit: {filename}")

            base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8000")
            audio_url = f"{base_url}/audio/{filename}"
            result["audio_url"] = audio_url

        # Save Assistant Message (store result as string or JSON string)
        # Note: We might want to store the audio URL in metadata in the future
        assistant_content = str(result.get("output", ""))
        if not assistant_content:
             assistant_content = str(result) # Fallback to full result if output is missing

        asst_msg = DBChatMessage(session_id=session_id, role="assistant", content=assistant_content)
        db.add(asst_msg)
        db.commit()

        return result

    except Exception as e:
        logging.error(f"Error during workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal workflow error.")


# -------------------------------------------------------
# TTS ENDPOINT
# -------------------------------------------------------
class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def generate_tts(request: TTSRequest, current_user: User = Depends(get_current_user)):
    """
    Generate audio for a given text string.
    Returns: { audio_url: str }
    """
    try:
        logging.info(f"Generating TTS for user {current_user.email}. Text length: {len(request.text)}")
        
        # Simple cache based on text hash
        import hashlib
        text_hash = hashlib.md5(request.text.encode("utf-8")).hexdigest()
        filename = f"{text_hash}.mp3"
        tts_path = os.path.join(AUDIO_DIR, filename)

        if not os.path.exists(tts_path):
            speech = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=request.text[:4096], # Limit for safety
                response_format="mp3"
            )
            with open(tts_path, "wb") as f:
                f.write(speech.read())
        else:
             logging.info(f"TTS Cache Hit: {filename}")

        base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8000")
        audio_url = f"{base_url}/audio/{filename}"
        
        return {"audio_url": audio_url}

    except Exception as e:
        logging.error(f"TTS generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------
# TRANSCRIBE ENDPOINT
# -------------------------------------------------------
@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe uploaded audio file using Whisper.
    Returns: { text: str, language: str }
    """
    try:
        # 1. Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await file.read())
            audio_path = tmp.name

        # 2. Whisper transcription with verbose response to get language
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        text = transcription.text.strip()
        language = getattr(transcription, "language", "en") # verbose_json returns language
        
        logging.info(f"Transcription ({language}): {text}")

        # Audit Log (optional for just transcription, or wait until chat)
        # audit_ledger.add_block(current_user.id, "TRANSCRIPTION", "User transcribed audio")
        
        # Cleanup
        os.unlink(audio_path)

        return {"text": text, "language": language}

    except Exception as e:
        logging.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------
# VOICE CHAT ENDPOINT (Legacy/Combined)
# -------------------------------------------------------
@app.post("/chat/voice")
async def chat_voice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user), # Protect this too if possible, but might be tricky with FormData
    # For simplicity in hackathon, we might skip strict auth on voice or pass token in headers manually
):
    """
    Handles voice queries. 
    NOTE: For strict auth, the frontend needs to send the Bearer token in headers.
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized.")

    try:
        # 1️⃣ Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await file.read())
            audio_path = tmp.name

        # 2️⃣ Whisper transcription
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

        text = transcription.text.strip()
        print(f"[VOICE INPUT] {text}")
        
        # Audit Log
        audit_ledger.add_block(current_user.id, "VOICE_QUERY", "User sent a voice message")

        # 3️⃣ Run healthcare workflow
        result = await workflow.run(
            user_input=text,
            query_for_classification=text
        )

        # Get the assistant output (string-safe)
        raw_output = result.get("output") if isinstance(result, dict) else result
        tts_input = raw_output if isinstance(raw_output, str) else str(raw_output)

        print("🧩 TTS Input:", tts_input[:200])

        # 4️⃣ Generate TTS audio (mp3)
        filename = f"{uuid4().hex}.mp3"
        tts_path = os.path.join(AUDIO_DIR, filename)

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=tts_input,
            response_format="mp3"
        )

        with open(tts_path, "wb") as f:
            f.write(speech.read())

        print("🧩 Saved:", tts_path, "size:", os.path.getsize(tts_path))

        # 5️⃣ Return combined JSON
        base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8000")

        return JSONResponse({
            "text": text,
            "assistant": result,
            "audio_url": f"{base_url}/audio/{filename}",
        })

    except Exception as e:
        logging.error(f"Voice processing failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# -------------------------------------------------------
# STATIC AUDIO SERVING
# -------------------------------------------------------
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(file_path, media_type="audio/mpeg")


# -------------------------------------------------------
# ROOT
# -------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "Healthcare Agent API is running."}


# -------------------------------------------------------
# RUN SERVER (DEV)
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
