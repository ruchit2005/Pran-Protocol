# MongoDB-based API endpoints (replaces SQLite)
import os
from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import json
import asyncio
from contextlib import asynccontextmanager

# MongoDB imports
from src.database.mongodb_manager import mongodb_manager
from src.database.mongodb_models import UserMongo, SessionMongo, MessageMongo, AuditLogMongo, ConsentAgreement
from src.security.encryption import PHIEncryptionManager
from src.compliance.disha_compliance import DISHAComplianceManager
from bson import ObjectId

# Initialize blockchain (auto-detect PostgreSQL or SQLite)
BLOCKCHAIN_DATABASE_URL = os.getenv("BLOCKCHAIN_DATABASE_URL")

if BLOCKCHAIN_DATABASE_URL:
    # Cloud PostgreSQL blockchain (shared across environments)
    from src.blockchain.postgres_blockchain import PostgresBlockchainAuditLogger
    blockchain_logger = PostgresBlockchainAuditLogger(BLOCKCHAIN_DATABASE_URL)
    logging.info("🌐 Using cloud PostgreSQL blockchain")
else:
    # Local SQLite blockchain (development only)
    from src.blockchain.private_blockchain import PrivateBlockchainAuditLogger
    blockchain_logger = PrivateBlockchainAuditLogger()
    logging.info("💾 Using local SQLite blockchain")

# Existing imports
from src.workflow import HealthcareWorkflow
from src.config import HealthcareConfig
from src.auth.security import create_access_token, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from jose import JWTError, jwt

# Initialize encryption manager
encryption_manager = PHIEncryptionManager()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting application...")
    
    # Verify SECRET_KEY is loaded
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        logger.error("❌ SECRET_KEY not set in environment!")
        raise RuntimeError("SECRET_KEY is required")
    logger.info(f"✅ SECRET_KEY loaded: {secret_key[:10]}...")
    
    await mongodb_manager.connect()
    
    # Create indexes for user_profiles collection
    try:
        await mongodb_manager.db.user_profiles.create_index("user_id", unique=True)
        logger.info("✅ Created user_profiles indexes")
    except Exception as e:
        logger.warning(f"Index creation: {e}")
    
    logger.info("✅ Application started successfully")
    yield
    # Shutdown
    logger.info("🛑 Shutting down application...")
    await mongodb_manager.close()
    logger.info("✅ Application shutdown complete")

app = FastAPI(
    title="Swastha - Healthcare AI Assistant",
    description="HIPAA-compliant healthcare chatbot with blockchain audit trail",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Initialize workflow
config = HealthcareConfig()
workflow = HealthcareWorkflow(config)

# Initialize DISHA compliance manager
compliance_manager = DISHAComplianceManager(
    blockchain_logger=blockchain_logger,
    master_key=os.getenv("MASTER_ENCRYPTION_KEY")
)
logger.info("✅ DISHA Compliance Manager initialized")

# Audio cache directory for TTS
AUDIO_DIR = os.path.join(os.getcwd(), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)
logger.info(f"✅ Audio directory ready: {AUDIO_DIR}")

# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str

class FirebaseLoginRequest(BaseModel):
    id_token: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfile(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: str

class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str

# Helper Functions
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current user from Firebase token (no JWT)"""
    from src.auth.firebase_auth import verify_firebase_token
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify Firebase token directly (run in thread to prevent blocking)
        decoded_token = await asyncio.to_thread(verify_firebase_token, token, clock_skew_seconds=10)
        if not decoded_token:
            raise credentials_exception
        
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise credentials_exception
        
        logger.info(f"🔍 Looking for user with firebase_uid: {firebase_uid}")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise credentials_exception
    
    # Find user by firebase_uid
    user = await mongodb_manager.db.users.find_one({"firebase_uid": firebase_uid})
    if user is None:
        logger.error(f"❌ User not found for firebase_uid: {firebase_uid}")
        raise credentials_exception
    
    logger.info(f"✅ Found user: {user.get('firebase_uid')}")
    return user
    return user

async def background_blockchain_log(log_id: ObjectId, user_id: ObjectId, action: str, resource_type: str, resource_id: Optional[ObjectId]):
    """Background task to log to blockchain and update MongoDB"""
    try:
        if blockchain_logger.enabled:
            blockchain_result = await blockchain_logger.log_action(
                str(user_id),
                action,
                {"resource_type": resource_type, "resource_id": str(resource_id)}
            )
            if blockchain_result:
                await mongodb_manager.db.audit_logs.update_one(
                    {"_id": log_id},
                    {
                        "$set": {
                            "blockchain_proof": {
                                "tx_hash": blockchain_result["tx_hash"],
                                "block_number": blockchain_result["block_number"],
                                "verified": True
                            },
                            "blockchain_status": "verified"
                        }
                    }
                )
                logger.info(f"✅ Blockchain audit confirmed for log {log_id}")
    except Exception as e:
        logger.error(f"❌ Background blockchain logging failed: {e}")

async def log_audit(user_id: ObjectId, action: str, resource_type: str, resource_id: Optional[ObjectId], request: Request):
    """Log action to audit log and blockchain (asynchronous)"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Create audit log with pending status
    audit_log = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "timestamp": datetime.utcnow(),
        "ip_address_hashed": encryption_manager.hash_for_audit(ip_address),
        "user_agent": user_agent,
        "result": "success",
        "blockchain_status": "pending"
    }
    
    # Store in MongoDB FIRST (Fast)
    result = await mongodb_manager.db.audit_logs.insert_one(audit_log)
    
    # Fire and forget blockchain logging
    if blockchain_logger.enabled:
        asyncio.create_task(background_blockchain_log(
            result.inserted_id, user_id, action, resource_type, resource_id
        ))


# Authentication Endpoints
@app.post("/auth/signup", response_model=Token)
async def signup(user: UserCreate, request: Request):
    """Create new user with encrypted data"""
    try:
        # Check if user exists
        existing = await mongodb_manager.db.users.find_one({
            "email_encrypted": encryption_manager.encrypt(user.email, encryption_manager.generate_user_salt())
        })
        
        # Since we can't easily search encrypted data, we'll store a hash for lookup
        email_hash = encryption_manager.hash_for_audit(user.email)
        existing = await mongodb_manager.db.users.find_one({"email_hash": email_hash})
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate user-specific salt
        user_salt = encryption_manager.generate_user_salt()
        
        # Create user document
        user_doc = {
            "firebase_uid": None,
            "email_encrypted": encryption_manager.encrypt(user.email, user_salt),
            "email_hash": email_hash,  # For lookup
            "password_hash": get_password_hash(user.password),
            "display_name_encrypted": None,
            "photo_url": None,
            "encryption_key_id": user_salt,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "mfa_enabled": False,
            "consent_agreements": [],
            "blockchain_identity": None
        }
        
        result = await mongodb_manager.db.users.insert_one(user_doc)
        
        # Audit log
        await log_audit(result.inserted_id, "SIGNUP", "user", result.inserted_id, request)
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": email_hash},  # Use hash for lookup
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signup failed")

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None):
    """Login with email/password"""
    try:
        # Find user by email hash
        email_hash = encryption_manager.hash_for_audit(form_data.username)
        user = await mongodb_manager.db.users.find_one({"email_hash": email_hash})
        
        if not user or not verify_password(form_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        await mongodb_manager.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Audit log
        await log_audit(user["_id"], "LOGIN", "user", user["_id"], request)
        
        # Create JWT
        access_token = create_access_token(
            data={"sub": email_hash},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/auth/firebase-login", response_model=Token)
async def firebase_login(request_data: FirebaseLoginRequest, request: Request):
    """Google OAuth login via Firebase"""
    try:
        from src.auth.firebase_auth import verify_firebase_token
        
        # Verify Firebase token with 10 seconds clock skew tolerance (run in thread)
        decoded_token = await asyncio.to_thread(verify_firebase_token, request_data.id_token, clock_skew_seconds=10)
        if not decoded_token:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")
        
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email") or request_data.email
        
        # Find or create user
        user = await mongodb_manager.db.users.find_one({"firebase_uid": firebase_uid})
        
        if not user:
            # Create new user
            user_salt = encryption_manager.generate_user_salt()
            email_hash = encryption_manager.hash_for_audit(email)
            
            user_doc = {
                "firebase_uid": firebase_uid,
                "email_encrypted": encryption_manager.encrypt(email, user_salt),
                "email_hash": email_hash,
                "password_hash": get_password_hash(os.urandom(32).hex()),  # Random password
                "display_name_encrypted": encryption_manager.encrypt(request_data.display_name, user_salt) if request_data.display_name else None,
                "photo_url": request_data.photo_url,
                "encryption_key_id": user_salt,
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "mfa_enabled": False,
                "consent_agreements": [],
                "blockchain_identity": None
            }
            
            result = await mongodb_manager.db.users.insert_one(user_doc)
            user = await mongodb_manager.db.users.find_one({"_id": result.inserted_id})
            
            await log_audit(result.inserted_id, "FIREBASE_SIGNUP", "user", result.inserted_id, request)
        else:
            # Update profile if changed
            updates = {}
            if request_data.display_name and user.get("display_name_encrypted"):
                user_salt = user["encryption_key_id"]
                decrypted_name = encryption_manager.decrypt(user["display_name_encrypted"], user_salt)
                if decrypted_name != request_data.display_name:
                    updates["display_name_encrypted"] = encryption_manager.encrypt(request_data.display_name, user_salt)
            
            if request_data.photo_url and user.get("photo_url") != request_data.photo_url:
                updates["photo_url"] = request_data.photo_url
            
            updates["last_login"] = datetime.utcnow()
            
            if updates:
                await mongodb_manager.db.users.update_one({"_id": user["_id"]}, {"$set": updates})
            
            await log_audit(user["_id"], "FIREBASE_LOGIN", "user", user["_id"], request)
        
        # Return the Firebase token directly (no JWT needed)
        return {"access_token": request_data.id_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Firebase login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/auth/me", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile (decrypted)"""
    try:
        user_salt = current_user.get("encryption_key_id")
        
        # Try to get email (decrypt if encrypted, otherwise use plain)
        if current_user.get("email"):
            email = current_user["email"]
        elif current_user.get("email_encrypted") and user_salt:
            email = encryption_manager.decrypt(current_user["email_encrypted"], user_salt)
        else:
            email = ""
        
        # Try to get display_name (decrypt if encrypted, otherwise use plain)
        if current_user.get("display_name"):
            display_name = current_user["display_name"]
        elif current_user.get("display_name_encrypted") and user_salt:
            display_name = encryption_manager.decrypt(current_user["display_name_encrypted"], user_salt)
        else:
            display_name = None
        
        return UserProfile(
            id=str(current_user["_id"]),
            email=email,
            display_name=display_name,
            photo_url=current_user.get("photo_url"),
            created_at=current_user["created_at"].isoformat()
        )
    except Exception as e:
        logger.error(f"Profile fetch error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CHAT & SESSION ENDPOINTS ====================

class ChatRequest(BaseModel):
    query: str  # Changed from 'message' to match frontend
    session_id: Optional[str] = None  # Changed to str for ObjectId compatibility
    generate_audio: Optional[bool] = False

# Return the full workflow result as a dict instead of structured response
# Frontend expects: {intent, output, yoga_recommendations, yoga_videos, etc.}

@app.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    req: Request = None
):
    """Process chat message with MongoDB storage, user profile, and history context"""
    try:
        user_id = current_user["_id"]
        user_salt = current_user["encryption_key_id"]
        
        # Get or create session
        if request.session_id:
            session = await mongodb_manager.db.sessions.find_one({"_id": ObjectId(request.session_id)})
            if not session or session["user_id"] != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create new session
            session_doc = {
                "user_id": user_id,
                "title": request.query[:50],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",
                "blockchain_session_hash": None
            }
            result = await mongodb_manager.db.sessions.insert_one(session_doc)
            session = await mongodb_manager.db.sessions.find_one({"_id": result.inserted_id})
        
        session_id = session["_id"]
        
        # --- USER PROFILE INTEGRATION WITH DISHA COMPLIANCE ---
        # Fetch or create user profile
        user_profile_raw = await mongodb_manager.db.user_profiles.find_one({"user_id": user_id})
        
        if not user_profile_raw:
            # Create empty profile
            profile_doc = {
                "user_id": user_id,
                "age": None,
                "gender": None,
                "medical_history": "[]",
                "allergies": "[]",
                "medications": "[]",
                "language_preference": "en",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await mongodb_manager.db.user_profiles.insert_one(profile_doc)
            user_profile_raw = await mongodb_manager.db.user_profiles.find_one({"user_id": user_id})
        
        # Anonymize user data (DISHA compliance)
        user_email = encryption_manager.decrypt(current_user.get("email_encrypted", ""), user_salt)
        compliance_data = await compliance_manager.process_user_data({
            **user_profile_raw,
            "email": user_email
        })
        anonymous_id = compliance_data['anonymized_data']['anonymous_id']
        anonymized_profile = compliance_data['anonymized_data']
        
        # Log data access to blockchain
        logger.info(f"📋 Data access logged for anonymous ID: {anonymous_id}")
        if compliance_data['access_audit'].get('blockchain_tx'):
            logger.info(f"⛓️ Blockchain TX: {compliance_data['access_audit']['blockchain_tx']}")
        
        # Build profile context with anonymized data
        profile_context = f"""
User Profile (Anonymized ID: {anonymous_id}):
- Age Range: {anonymized_profile.get('age_range', 'Unknown')}
- Gender: {anonymized_profile.get('gender', 'Unknown')}
- Medical Conditions: {anonymized_profile.get('medical_history', [])}
- Allergies: {anonymized_profile.get('allergies', [])}
- Current Medications: {anonymized_profile.get('medications', [])}
"""
        
        # --- CHAT HISTORY INTEGRATION ---
        # Fetch last 5 messages from this session
        history_msgs = await mongodb_manager.db.messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).to_list(length=None)
        
        history_context = ""
        if history_msgs:
            history_context += "\n\nPrevious conversation:\n"
            for i, msg in enumerate(history_msgs[-5:], 1):
                role = msg.get("role", "unknown")
                content = msg.get("content")
                # Handle content that might be a dict
                if isinstance(content, dict):
                    content = content.get("output", str(content))
                history_context += f"{i}. {role.capitalize()}: {content}\n"
        
        # Combine context
        full_context_query = f"{profile_context}\n{history_context}\nUser Query: {request.query}"
        
        # Store user message (plain text)
        user_msg_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "role": "user",
            "content": request.query,
            "intent": None,
            "timestamp": datetime.utcnow(),
            "ip_address": req.client.host if req else "unknown",
            "blockchain_tx_hash": None
        }
        await mongodb_manager.db.messages.insert_one(user_msg_doc)
        
        # Log to blockchain (if enabled)
        if blockchain_logger.enabled:
            try:
                tx_hash = await blockchain_logger.log_action(
                    user_id=str(user_id),
                    action="USER_MESSAGE",
                    data={"session_id": str(session_id), "message_preview": request.query[:20]}
                )
                user_msg_doc["blockchain_tx_hash"] = tx_hash
            except Exception as e:
                logger.warning(f"Blockchain logging failed: {e}")
        
        # Process with healthcare workflow WITH CONTEXT
        result = await workflow.run(
            user_input=request.query,
            query_for_classification=full_context_query,  # Pass full context
            user_profile=user_profile_raw  # Pass profile for potential updates
        )
        
        # Process response with DISHA compliance
        compliant_response = await compliance_manager.process_ai_response(
            anonymous_id=anonymous_id,
            user_query=request.query,
            ai_response=result
        )
        
        # Log blockchain transaction for medical advice
        if compliant_response['blockchain_audit']:
            blockchain_tx = compliant_response['blockchain_audit'].get('blockchain_tx')
            if blockchain_tx:
                logger.info(f"⛓️ Medical advice logged to blockchain: {blockchain_tx}")
        
        # Check if workflow updated the profile
        if result.get("profile_updated"):
            await mongodb_manager.db.user_profiles.update_one(
                {"user_id": user_id},
                {"$set": {
                    "age": user_profile_raw.get("age"),
                    "gender": user_profile_raw.get("gender"),
                    "medical_history": user_profile_raw.get("medical_history"),
                    "allergies": user_profile_raw.get("allergies"),
                    "medications": user_profile_raw.get("medications"),
                    "updated_at": datetime.utcnow()
                }}
            )
            logger.info(f"Updated user profile for {user_id}")
        
        # --- TTS AUDIO GENERATION (if requested) ---
        audio_url = None
        if request.generate_audio:
            from openai import OpenAI
            import hashlib
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Get text to speak
            raw_output = result.get("output") if isinstance(result, dict) else result
            tts_input = raw_output if isinstance(raw_output, str) else str(raw_output)
            
            # Create cache filename
            text_hash = hashlib.md5(tts_input.encode("utf-8")).hexdigest()
            filename = f"{text_hash}.mp3"
            tts_path = os.path.join(AUDIO_DIR, filename)
            
            # Generate if not cached
            if not os.path.exists(tts_path):
                logger.info(f"Generating TTS for session {session_id}")
                try:
                    speech = client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=tts_input[:4096],
                        response_format="mp3"
                    )
                    with open(tts_path, "wb") as f:
                        f.write(speech.read())
                    logger.info(f"TTS generated: {filename}")
                except Exception as e:
                    logger.error(f"TTS generation failed: {e}")
            else:
                logger.info(f"TTS cache hit: {filename}")
            
            base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8000")
            audio_url = f"{base_url}/audio/{filename}"
        
        # Store assistant response
        assistant_content = str(result.get("output", ""))
        if not assistant_content:
            assistant_content = str(result)
        
        assistant_msg_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "role": "assistant",
            "content": assistant_content,
            "intent": result.get("intent"),
            "timestamp": datetime.utcnow(),
            "ip_address": req.client.host if req else "unknown",
            "blockchain_tx_hash": None
        }
        await mongodb_manager.db.messages.insert_one(assistant_msg_doc)
        
        # Update session timestamp
        await mongodb_manager.db.sessions.update_one(
            {"_id": session_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        # Audit log
        await log_audit(
            user_id=user_id,
            action="CHAT_MESSAGE",
            resource_type="message",
            resource_id=session_id,
            request=req
        )
        
        # Return full workflow result with DISHA compliance metadata
        return {
            **result,
            "session_id": str(session_id),
            "timestamp": datetime.utcnow().isoformat(),
            "audio_url": audio_url,
            "compliance": {
                "status": "DISHA_COMPLIANT",
                "anonymized": True,
                "verifiable": True,
                "anonymous_id": anonymous_id,
                "blockchain_tx": compliant_response['blockchain_audit'].get('blockchain_tx') if compliant_response['blockchain_audit'] else None,
                "signature": compliant_response['response'].get('signature'),
                "public_key_fingerprint": compliant_response['response'].get('public_key_fingerprint')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/alerts")
async def get_health_alerts():
    """Get real-time health alerts to display in the frontend widget"""
    try:
        # Access the advisory chain from the workflow
        if hasattr(workflow, 'advisory_chain'):
             # Run in thread pool to avoid blocking async loop since requests is sync
            articles = await asyncio.to_thread(workflow.advisory_chain.fetch_headlines)
            
            # Format for frontend
            alerts = []
            for a in articles:
                alerts.append({
                    "title": a.get("title"),
                    "url": a.get("url", "#"),
                    "source": a.get("source", {}).get("name", "Unknown"),
                    "publishedAt": a.get("publishedAt"),
                    "description": a.get("description", "")
                })
            return {"alerts": alerts}
        else:
            return {"alerts": []}
    except Exception as e:
        logger.error(f"Alerts fetch error: {e}", exc_info=True)
        return {"alerts": []}


@app.get("/sessions")
async def get_sessions(current_user: dict = Depends(get_current_user)):
    """Get user's chat sessions"""
    try:
        user_id = current_user["_id"]
        user_salt = current_user["encryption_key_id"]
        
        cursor = mongodb_manager.db.sessions.find(
            {"user_id": user_id, "status": "active"}
        ).sort("updated_at", -1).limit(50)
        
        sessions = []
        async for session in cursor:
            sessions.append({
                "id": str(session["_id"]),
                "title": session.get("title", "Untitled"),
                "created_at": session["created_at"].isoformat(),
                "updated_at": session["updated_at"].isoformat()
            })
        
        return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/messages")
@app.get("/sessions/{session_id}/history")  # Alias for frontend compatibility
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a session (decrypted)"""
    try:
        user_id = current_user["_id"]
        user_salt = current_user["encryption_key_id"]
        
        # Verify session ownership
        session = await mongodb_manager.db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session or session["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        cursor = mongodb_manager.db.messages.find(
            {"session_id": ObjectId(session_id)}
        ).sort("timestamp", 1)
        
        messages = []
        async for msg in cursor:
            content = msg.get("content", "")
            
            messages.append({
                "role": msg["role"],
                "content": content,
                "timestamp": msg["timestamp"].isoformat()
            })
        
        return {"messages": messages}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get messages error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Archive a session"""
    try:
        user_id = current_user["_id"]
        
        # Verify session ownership
        session = await mongodb_manager.db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session or session["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Archive instead of delete (HIPAA compliance)
        await mongodb_manager.db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "archived", "updated_at": datetime.utcnow()}}
        )
        
        return {"message": "Session archived successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIO ENDPOINTS ====================

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile,
    current_user: dict = Depends(get_current_user)
):
    """Transcribe uploaded audio file using Whisper"""
    import tempfile
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await file.read())
            audio_path = tmp.name

        # Whisper transcription
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        text = transcription.text.strip()
        language = getattr(transcription, "language", "en")
        
        logger.info(f"Transcription ({language}): {text}")

        # Cleanup
        os.unlink(audio_path)
        
        return {"text": text, "language": language}
    
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# TTS AUDIO ENDPOINT
# -------------------------------------------------------
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated TTS audio files"""
    from fastapi.responses import FileResponse
    
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# -------------------------------------------------------
# DISHA COMPLIANCE ENDPOINTS
# -------------------------------------------------------
@app.post("/compliance/verify")
async def verify_response_signature(signature: str, response_data: str):
    """
    Verify that an AI response is authentic and hasn't been tampered with
    """
    try:
        signed_response = json.loads(response_data)
        is_valid = compliance_manager.credential_manager.verify_response(signed_response)
        
        return {
            "verified": is_valid,
            "message": "Response signature is valid" if is_valid else "Invalid signature - response may have been tampered with"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/compliance/audit/{anonymous_id}")
async def get_audit_trail(
    anonymous_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get blockchain audit trail for a user (requires authentication)
    User can only access their own audit trail
    """
    try:
        user_id = current_user["_id"]
        user_salt = current_user["encryption_key_id"]
        user_email = encryption_manager.decrypt(current_user.get("email_encrypted", ""), user_salt)
        
        # Verify user owns this anonymous ID
        user_anon_id = compliance_manager.anonymizer.create_anonymous_id(user_email)
        
        if user_anon_id != anonymous_id:
            raise HTTPException(status_code=403, detail="Access denied - not your audit trail")
        
        # Fetch audit trail directly from blockchain
        audit_trail = blockchain_logger.blockchain.get_audit_trail(anonymous_id)
        
        return {
            "anonymous_id": anonymous_id,
            "audit_trail": audit_trail,
            "compliance_status": "DISHA_COMPLIANT",
            "total_records": len(audit_trail)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit trail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/anonymous-id")
async def get_anonymous_id(current_user: dict = Depends(get_current_user)):
    """
    Get the authenticated user's anonymous ID for blockchain queries
    """
    try:
        user_salt = current_user["encryption_key_id"]
        user_email = encryption_manager.decrypt(current_user.get("email_encrypted", ""), user_salt)
        
        # Generate anonymous ID using compliance manager
        anonymous_id = compliance_manager.anonymizer.create_anonymous_id(user_email)
        
        return {
            "anonymous_id": anonymous_id,
            "email": user_email  # Include for verification
        }
    except Exception as e:
        logger.error(f"Anonymous ID error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/stats")
async def get_blockchain_statistics():
    """
    Get private blockchain statistics (public endpoint)
    """
    try:
        stats = blockchain_logger.get_statistics()
        
        return {
            "blockchain_type": "Private SQLite Blockchain",
            "features": [
                "Zero gas fees",
                "Instant transactions",
                "HIPAA compliant (data never leaves server)",
                "Immutable audit trail",
                "Tamper detection"
            ],
            **stats
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
