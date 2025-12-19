# MongoDB-based API endpoints (replaces SQLite)
import os
from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
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
from openai import OpenAI
from sarvamai import SarvamAI
import base64
import shutil
import hashlib
import wave
import io

# Initialize blockchain (auto-detect PostgreSQL or SQLite)
BLOCKCHAIN_DATABASE_URL = os.getenv("BLOCKCHAIN_DATABASE_URL")

blockchain_logger = None
try:
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
except Exception as e:
    logging.warning(f"⚠️ Blockchain initialization failed: {e}")
    logging.warning("⚠️ Continuing without blockchain logging")
    blockchain_logger = None

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
    
    # Fetch initial health news
    await fetch_initial_health_news()
    
    # Start background task to refresh health news every hour
    refresh_task = asyncio.create_task(refresh_health_news_periodically())
    
    logger.info("✅ Application started successfully")
    yield
    
    # Cancel background task on shutdown
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
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
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://pran-protocol-beff.vercel.app",  # All Vercel deployments
        "https://*.ngrok-free.app",  # Ngrok tunnels
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Initialize workflow
config = HealthcareConfig()
workflow = HealthcareWorkflow(config)

# Background task to refresh health news every hour
async def refresh_health_news_periodically():
    """Background task that refreshes health news every hour"""
    while True:
        try:
            await asyncio.sleep(3600)  # Wait 1 hour
            if hasattr(workflow, 'advisory_chain'):
                print("🔄 Auto-refreshing health news (hourly)...")
                await asyncio.to_thread(workflow.advisory_chain.fetch_headlines)
                print("✅ Health news refreshed")
        except Exception as e:
            print(f"⚠️ Auto-refresh failed: {e}")

# Fetch initial health news data on startup (so it's ready immediately)
async def fetch_initial_health_news():
    """Fetch health news once on startup"""
    if hasattr(workflow, 'advisory_chain'):
        try:
            print("📰 Fetching initial Uttarakhand health news...")
            await asyncio.to_thread(workflow.advisory_chain.fetch_headlines)
            print("✅ Health news loaded and cached")
        except Exception as e:
            print(f"⚠️ Initial health news fetch failed: {e}")

# Initialize DISHA compliance manager
compliance_manager = DISHAComplianceManager(
    blockchain_logger=blockchain_logger,
    master_key=os.getenv("MASTER_ENCRYPTION_KEY")
)
logger.info("✅ DISHA Compliance Manager initialized")

# Audio cache directory for TTS
# Upload directory
UPLOAD_DIR = "uploads"
AUDIO_DIR = "audio_cache"
os.makedirs(UPLOAD_DIR, exist_ok=True)
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
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    previous_conditions: Optional[List[str]] = []
    address: Optional[dict] = None

class AddressModel(BaseModel):
    street: str = ""
    district: str = ""
    state: str = ""
    pincode: str = ""

class UserProfileUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    
    # Frontend sends these as Lists (e.g., ["Diabetes", "Asthma"])
    medical_history: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    previous_conditions: Optional[List[str]] = []
    
    # Frontend sends address as an object
    address: Optional[AddressModel] = None

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
        if blockchain_logger and blockchain_logger.enabled:
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
    if blockchain_logger and blockchain_logger.enabled:
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
        
        # Decrypt age
        age = None
        if current_user.get("age_encrypted") and user_salt:
            decrypted_age = encryption_manager.decrypt(current_user["age_encrypted"], user_salt)
            try:
                age = int(decrypted_age)
            except (ValueError, TypeError):
                age = None
        elif current_user.get("age"):
            # Fallback for non-encrypted age
            age = current_user.get("age")
        
        # Decrypt gender
        gender = None
        if current_user.get("gender_encrypted") and user_salt:
            gender = encryption_manager.decrypt(current_user["gender_encrypted"], user_salt)
        elif current_user.get("gender"):
            # Fallback for non-encrypted gender
            gender = current_user.get("gender")
        
        # Decrypt address
        address = None
        if current_user.get("address_encrypted") and user_salt:
            import json
            decrypted_address = encryption_manager.decrypt(current_user["address_encrypted"], user_salt)
            try:
                address = json.loads(decrypted_address)
            except (json.JSONDecodeError, TypeError):
                address = None
        elif current_user.get("address"):
            # Fallback for non-encrypted address
            address = current_user.get("address")
        
        # Decrypt medical data
        medical_history = []
        if current_user.get("medical_history_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["medical_history_encrypted"], user_salt)
            medical_history = [h.strip() for h in decrypted.split(",") if h.strip()]
        
        medications = []
        if current_user.get("medications_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["medications_encrypted"], user_salt)
            medications = [m.strip() for m in decrypted.split(",") if m.strip()]
        
        previous_conditions = []
        if current_user.get("previous_conditions_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["previous_conditions_encrypted"], user_salt)
            previous_conditions = [p.strip() for p in decrypted.split(",") if p.strip()]
        
        return UserProfile(
            id=str(current_user["_id"]),
            email=email,
            display_name=display_name,
            photo_url=current_user.get("photo_url"),
            created_at=current_user["created_at"].isoformat(),
            age=age,
            gender=gender,
            medical_history=medical_history,
            medications=medications,
            previous_conditions=previous_conditions,
            address=address
        )
    except Exception as e:
        logger.error(f"Profile fetch error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/profile")
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """
    Updates the user profile from the onboarding questionnaire/profile modal.
    Encrypts sensitive medical data before saving to MongoDB.
    """
    try:
        user_id = current_user["_id"]
        logger.info(f"📝 Updating profile for user: {user_id}")
        logger.info(f"Profile data received: age={profile_data.age}, gender={profile_data.gender}, medical_history={profile_data.medical_history}")
        
        # 1. Get the user's unique salt for encryption
        user_salt = current_user.get("encryption_key_id")
        
        # Safety check: if no salt exists (rare), create one
        if not user_salt:
            logger.warning(f"No encryption key found for user {user_id}, creating one...")
            user_salt = encryption_manager.generate_user_salt()
            await mongodb_manager.db.users.update_one(
                {"_id": user_id}, 
                {"$set": {"encryption_key_id": user_salt}}
            )
            logger.info(f"✅ Created encryption key for user {user_id}")

        # 2. Prepare the update dictionary
        update_fields = {}
        
        # 3. ENCRYPT All Profile Data (HIPAA Compliance)
        # Basic Fields - also encrypted for privacy
        if profile_data.age is not None:
            encrypted_age = encryption_manager.encrypt(str(profile_data.age), user_salt)
            update_fields["age_encrypted"] = encrypted_age
            logger.info(f"✅ Encrypted age")
        
        if profile_data.gender:
            encrypted_gender = encryption_manager.encrypt(profile_data.gender, user_salt)
            update_fields["gender_encrypted"] = encrypted_gender
            logger.info(f"✅ Encrypted gender")
        
        if profile_data.address:
            # Convert address to JSON string, then encrypt
            import json
            address_json = json.dumps(profile_data.address.dict())
            encrypted_address = encryption_manager.encrypt(address_json, user_salt)
            update_fields["address_encrypted"] = encrypted_address
            logger.info(f"✅ Encrypted address")

        # Medical data encryption
        # We convert lists to strings, then encrypt them
        if profile_data.medical_history:
            combined_history = ", ".join(profile_data.medical_history)
            encrypted_history = encryption_manager.encrypt(combined_history, user_salt)
            update_fields["medical_history_encrypted"] = encrypted_history
            logger.info(f"✅ Encrypted medical history: {len(profile_data.medical_history)} items")
        
        if profile_data.previous_conditions:
             # Merge previous conditions into medical history or store separately
             combined_prev = ", ".join(profile_data.previous_conditions)
             encrypted_prev = encryption_manager.encrypt(combined_prev, user_salt)
             update_fields["previous_conditions_encrypted"] = encrypted_prev
             logger.info(f"✅ Encrypted previous conditions: {len(profile_data.previous_conditions)} items")

        if profile_data.medications:
            combined_meds = ", ".join(profile_data.medications)
            encrypted_meds = encryption_manager.encrypt(combined_meds, user_salt)
            update_fields["medications_encrypted"] = encrypted_meds
            logger.info(f"✅ Encrypted medications: {len(profile_data.medications)} items")

        if not update_fields:
            logger.warning("No fields to update")
            return {"message": "No changes to update"}

        # 4. Update MongoDB users collection
        logger.info(f"💾 Saving {len(update_fields)} encrypted fields to MongoDB...")
        result = await mongodb_manager.db.users.update_one(
            {"_id": user_id},
            {"$set": update_fields}
        )
        
        logger.info(f"✅ MongoDB update result: matched={result.matched_count}, modified={result.modified_count}")
        
        # Log this significant event
        await log_audit(user_id, "PROFILE_UPDATE", "user", user_id, request)
        
        return {"message": "Profile updated successfully", "status": "success"}

    except Exception as e:
        logger.error(f"❌ Error updating profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



# ==================== TTS UTILITIES ====================

def stitch_wavs(wav_bytes_list):
    """
    Concatenate multiple WAV byte objects into a single WAV using 'wave' module.
    More robust than byte manipulation.
    """
    if not wav_bytes_list:
        return b""
    if len(wav_bytes_list) == 1:
        return wav_bytes_list[0]

    output = io.BytesIO()
    
    try:
        # Read parameters from first file
        with wave.open(io.BytesIO(wav_bytes_list[0]), 'rb') as first_wav:
            params = first_wav.getparams()
            
        with wave.open(output, 'wb') as out_wav:
            out_wav.setparams(params)
            
            for i, wav_data in enumerate(wav_bytes_list):
                 with wave.open(io.BytesIO(wav_data), 'rb') as w:
                     # Verify params match (simple check)
                     if w.getparams()[:3] != params[:3]: # channels, sampwidth, framerate
                         logging.warning(f"⚠️ Chunk {i} has different WAV params! Stitching might sound weird.")
                     
                     out_wav.writeframes(w.readframes(w.getnframes()))
                     
        return output.getvalue()
        
    except Exception as e:
        logging.error(f"❌ Error stitching WAVs with wave module: {e}")
        # Fallback to simple concatenation if wave module fails (unlikely)
        return b"".join(wav_bytes_list)

def chunk_text(text, max_chars=450):
    """
    Split text into chunks of max_chars, preserving sentence boundaries where possible.
    """
    chunks = []
    current_chunk = ""
    
    # Split by double newlines first (paragraphs)
    paragraphs = text.replace("\r", "").split("\n")
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        sentences = [s.strip() + "." for s in para.split(".") if s.strip()]
        if not sentences:
            sentences = [para] # Fallback if no periods
            
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                
                # If single sentence is massive, split it hardly
                if len(current_chunk) > max_chars:
                     # This logic can be improved, but strict cutoff is better than failure
                     while len(current_chunk) > max_chars:
                         chunks.append(current_chunk[:max_chars])
                         current_chunk = current_chunk[max_chars:]
                         
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

# ==================== TTS ENDPOINT (SARVAM AI) ====================

class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = "en-IN"

@app.post("/tts")
async def text_to_speech(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """
    Convert text to speech using Sarvam AI with caching and speed control
    """
    try:
        import re
        
        # Clean text for TTS (remove all formatting and special characters)
        text_for_tts = request.text
        
        # Remove citations
        text_for_tts = re.sub(r'\[Source:.*?\]', '', text_for_tts)
        text_for_tts = re.sub(r'\[\d+\]', '', text_for_tts)
        text_for_tts = re.sub(r'\[Citation:.*?\]', '', text_for_tts)
        
        # Remove markdown formatting
        text_for_tts = re.sub(r'#{1,6}\s*', '', text_for_tts)  # Headers
        text_for_tts = re.sub(r'\*\*(.*?)\*\*', r'\1', text_for_tts)  # Bold
        text_for_tts = re.sub(r'\*(.*?)\*', r'\1', text_for_tts)  # Italic
        text_for_tts = re.sub(r'`(.*?)`', r'\1', text_for_tts)  # Code
        text_for_tts = re.sub(r'^\s*[-*+]\s+', '', text_for_tts, flags=re.MULTILINE)  # Lists
        text_for_tts = re.sub(r'^\s*\d+\.\s+', '', text_for_tts, flags=re.MULTILINE)  # Numbered lists
        
        # Remove emojis and special symbols
        text_for_tts = re.sub(r'[^\w\s,.!?;:()\-\'/"]', '', text_for_tts)
        
        # Clean up spacing
        text_for_tts = re.sub(r'\n+', '. ', text_for_tts)
        text_for_tts = re.sub(r'\s+', ' ', text_for_tts).strip()
        
        # 1. Caching Mechanism
        # Normalize text for hash: strip and lower to catch duplicates better
        normalized_text = text_for_tts.strip().lower()
        # Include params in hash to differentiate quality settings
        hash_input = f"{normalized_text}_{request.language_code}_anushka_v2_24k"
        text_hash = hashlib.md5(hash_input.encode()).hexdigest()
        cache_filename = f"tts_{text_hash}.wav"
        cache_path = os.path.join(AUDIO_DIR, cache_filename)
        
        # Check if already cached
        if os.path.exists(cache_path):
            file_size = os.path.getsize(cache_path)
            logger.info(f"🔊 Cache hit for TTS: {cache_filename} (Size: {file_size} bytes)")
            
            # Additional check: If file is too small, it might be corrupted/failed previous run
            if file_size > 1000:
                with open(cache_path, "rb") as f:
                    audio_content = f.read()
                    audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                    return {"audio_url": f"data:audio/wav;base64,{audio_base64}"}
            else:
                logger.warning(f"⚠️ Cache file too small ({file_size}b), regenerating: {cache_filename}")
        else:
             logger.info(f"🔊 Cache miss for TTS: {cache_filename}")
        
        # 2. Force reload env to ensure key is picked up
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
             load_dotenv(override=True)
             api_key = os.getenv("SARVAM_API_KEY")
             
        if not api_key:
             logger.error("❌ SARVAM_API_KEY not found in env even after reload")
             raise HTTPException(status_code=500, detail="TTS service not configured (missing key)")

        client = SarvamAI(api_subscription_key=api_key)
        
        # 3. Process Text with Chunking (use cleaned text without citations)
        text_full = text_for_tts.strip()
        if not text_full:
             raise HTTPException(status_code=400, detail="Text is empty")

        # Lower chunk size even more to be safe (400 chars)
        chunks = chunk_text(text_full, max_chars=400) 
        logger.info(f"🔊 Generating TTS for {len(text_full)} chars | Split into {len(chunks)} chunks")
        
        audio_segments = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"  • Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars): {chunk[:30]}...")
            logger.info(f"  • Language: {request.language_code}")
            try:
                response = client.text_to_speech.convert(
                    text=chunk,
                    target_language_code=request.language_code,
                    speaker="anushka",
                    pace=0.9,              # Slow and steady
                    pitch=-0.2,             # Slightly lower for softer tone
                    loudness=1.0,           # Balanced loudness
                    speech_sample_rate=24000, # Premium 24kHz quality
                    enable_preprocessing=True
                )
                
                if hasattr(response, "audios") and response.audios:
                    b64_data = response.audios[0]
                    # Verify b64 data
                    if len(b64_data) < 100:
                        logger.warning(f"  ⚠️ Chunk {i} returned suspiciously small audio")
                    
                    audio_segments.append(base64.b64decode(b64_data))
                    logger.info(f"  ✅ Chunk {i+1} success")
                else:
                    logger.warning(f"  ❌ Chunk {i} failed: No audio in response")
            except Exception as e:
                logger.error(f"  ❌ Chunk {i} error: {e}")
                # Wait a bit between chunks to avoid rate limits?
                await asyncio.sleep(0.5)
        
        if not audio_segments:
             raise HTTPException(status_code=500, detail="Failed to generate audio for all chunks")

        # 4. Stitch Audio
        final_audio = stitch_wavs(audio_segments)
        final_b64 = base64.b64encode(final_audio).decode('utf-8')
        
        logger.info(f"🔊 Stitched Audio Size: {len(final_audio)} bytes")

        # 5. Save to Cache
        try:
            with open(cache_path, "wb") as f:
                f.write(final_audio)
            logger.info(f"💾 Saved stitched TTS to cache: {cache_filename}")
        except Exception as e:
            logger.error(f"⚠️ Failed to cache TTS audio: {e}")

        return {
            "audio_url": f"data:audio/wav;base64,{final_b64}"
        }

    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHAT & SESSION ENDPOINTS ====================

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    locale: str = Form("en"),  # Accept locale from form data
    current_user: dict = Depends(get_current_user)
):
    """
    Transcribes uploaded audio file using OpenAI Whisper with language hint.
    Expects 'file' and 'locale' in multipart/form-data.
    """
    temp_filename = f"temp_{file.filename}"
    try:
        # Save uploaded file temporarily
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Explicitly get API Key with fallbacks
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_1") or os.getenv("OPENAI_API_KEY_2")
        
        if not api_key:
            # Try reloading dotenv just in case
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_1") or os.getenv("OPENAI_API_KEY_2")
            
        if not api_key:
            logger.error("❌ OPENAI_API_KEY (or variants) not found in environment variables!")
            raise HTTPException(status_code=500, detail="Server misconfiguration: OPENAI_API_KEY missing.")
        
        # Initialize OpenAI client with explicit key
        client = OpenAI(api_key=api_key)
        
        # Map locale to Whisper language codes
        language_hint = "hi" if locale == "hi" else "en"
        
        with open(temp_filename, "rb") as audio_file:
            # Pass language hint to help Whisper recognize the correct language
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language=language_hint,  # Tell Whisper to expect this language
                response_format="verbose_json"  # Get language detection info
            )
        
        detected_language = getattr(transcript, 'language', language_hint)
        logger.info(f"✅ Transcription successful: '{transcript.text[:50]}...' (hint: {language_hint}, detected: {detected_language})")
        return {"text": transcript.text, "language": detected_language}

    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Cleanup temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

class ChatRequest(BaseModel):
    query: str  # Changed from 'message' to match frontend
    session_id: Optional[str] = None  # Changed to str for ObjectId compatibility
    generate_audio: Optional[bool] = False
    latitude: Optional[float] = None  # User's location for emergency services
    longitude: Optional[float] = None
    locale: Optional[str] = "en"  # User's language preference (en or hi)

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
        # Debug: Log the raw request body (using print for visibility)
        print(f"🔍 [RAW REQUEST] ChatRequest object:")
        print(f"   - query: {request.query[:50]}...")
        print(f"   - session_id: {request.session_id}")
        print(f"   - generate_audio: {request.generate_audio}")
        print(f"   - locale: {request.locale}")
        print(f"   - latitude: {request.latitude}")
        print(f"   - longitude: {request.longitude}")
        print(f"   - latitude type: {type(request.latitude)}")
        print(f"   - longitude type: {type(request.longitude)}")
        
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
        # Use current_user data directly (from users collection)
        # Decrypt age
        age = None
        if current_user.get("age_encrypted") and user_salt:
            decrypted_age = encryption_manager.decrypt(current_user["age_encrypted"], user_salt)
            try:
                age = int(decrypted_age)
            except (ValueError, TypeError):
                age = None
        elif current_user.get("age"):
            age = current_user.get("age")
        
        # Decrypt gender
        gender = None
        if current_user.get("gender_encrypted") and user_salt:
            gender = encryption_manager.decrypt(current_user["gender_encrypted"], user_salt)
        elif current_user.get("gender"):
            gender = current_user.get("gender")
        
        user_profile_raw = {
            "user_id": user_id,
            "age": age,
            "gender": gender,
            "medical_history": "[]",
            "allergies": "[]",
            "medications": "[]",
            "language_preference": "en"
        }
        
        # Decrypt medical data if encrypted
        if current_user.get("medical_history_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["medical_history_encrypted"], user_salt)
            user_profile_raw["medical_history"] = decrypted
        
        if current_user.get("medications_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["medications_encrypted"], user_salt)
            user_profile_raw["medications"] = decrypted
        
        if current_user.get("allergies_encrypted") and user_salt:
            decrypted = encryption_manager.decrypt(current_user["allergies_encrypted"], user_salt)
            user_profile_raw["allergies"] = decrypted
        
        # Fetch recent documents for context
        document_context = ""
        full_documents_text = ""  # For detailed document queries
        try:
            recent_docs = await mongodb_manager.db.user_documents.find(
                {"user_id": user_id, "status": "processed"}
            ).sort("upload_date", -1).limit(5).to_list(length=5)
            
            logger.info(f"📄 Found {len(recent_docs)} processed documents for user")
            
            if recent_docs:
                doc_summaries = []
                doc_full_texts = []
                
                for doc in recent_docs:
                    analysis = doc.get("analysis", {})
                    if analysis and analysis.get("analyzed"):
                        summary = f"📄 {doc['file_name']}"
                        if analysis.get("summary"):
                            summary += f": {analysis['summary']}"
                        if analysis.get("medications"):
                            summary += f" | Medications: {', '.join(analysis['medications'][:3])}"
                        if analysis.get("diagnoses"):
                            summary += f" | Diagnoses: {', '.join(analysis['diagnoses'][:3])}"
                        doc_summaries.append(summary)
                        
                        # Decrypt full text for document queries
                        if doc.get("full_text_encrypted"):
                            try:
                                full_text = encryption_manager.decrypt(doc["full_text_encrypted"], user_salt)
                                doc_full_texts.append(f"\n--- {doc['file_name']} ---\n{full_text[:2000]}")  # Limit to 2000 chars per doc
                            except Exception as e:
                                logger.error(f"Failed to decrypt document text: {e}")
                
                if doc_summaries:
                    document_context = "\n\nRecent Medical Documents:\n" + "\n".join(doc_summaries)
                    logger.info(f"✅ Document context created with {len(doc_summaries)} summaries")
                
                if doc_full_texts:
                    full_documents_text = "\n\n".join(doc_full_texts)
                    logger.info(f"✅ Full document text: {len(full_documents_text)} chars from {len(doc_full_texts)} docs")
        except Exception as e:
            logger.error(f"Failed to fetch document context: {e}")
        
        user_profile_raw["document_context"] = document_context
        user_profile_raw["full_documents_text"] = full_documents_text  # For detailed queries
        
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
{document_context}
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
        if blockchain_logger and blockchain_logger.enabled:
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
        # Determine response language - detect from actual user input text
        def detect_language_from_text(text: str, url_locale: str) -> str:
            """Detect language from actual characters in user input"""
            # Count Devanagari characters (Hindi: U+0900 to U+097F)
            devanagari_count = sum(1 for char in text if '\u0900' <= char <= '\u097F')
            # Count English/ASCII alphabetic characters
            english_count = sum(1 for char in text if char.isascii() and char.isalpha())
            
            logger.info(f"📊 Language Analysis of '{text}':")
            logger.info(f"   - Devanagari chars: {devanagari_count}")
            logger.info(f"   - English chars: {english_count}")
            logger.info(f"   - URL locale: {url_locale}")
            
            # If user typed Hindi characters, respond in Hindi
            if devanagari_count >= 3:
                logger.info(f"   → Decision: HINDI (has {devanagari_count} Devanagari chars)")
                return "Hindi (Devanagari script, not Urdu)"
            # If user typed English, respond in English
            elif english_count > devanagari_count:
                logger.info(f"   → Decision: ENGLISH (has {english_count} English chars)")
                return "English"
            # If ambiguous (no clear text), use URL locale as fallback
            else:
                fallback = "Hindi (Devanagari script, not Urdu)" if url_locale == "hi" else "English"
                logger.info(f"   → Decision: FALLBACK to {fallback}")
                return fallback
        
        response_language = detect_language_from_text(request.query, request.locale)
        logger.info(f"🔤 FINAL Response Language: {response_language}")
        
        # Debug logging for location
        logger.info(f"🔍 [BACKEND STEP 1] Request received:")
        logger.info(f"   - request.latitude: {request.latitude} (type: {type(request.latitude).__name__})")
        logger.info(f"   - request.longitude: {request.longitude} (type: {type(request.longitude).__name__})")
        logger.info(f"   - locale: {request.locale}")
        
        user_location_tuple = None
        if request.latitude and request.longitude:
            user_location_tuple = (request.latitude, request.longitude)
            logger.info(f"✅ [BACKEND STEP 2] Created user_location tuple: {user_location_tuple}")
        else:
            logger.warning(f"⚠️ [BACKEND STEP 2] No location - latitude or longitude missing")
        
        logger.info(f"🚀 [BACKEND STEP 3] Calling workflow.run with user_location={user_location_tuple}")
        
        result = await workflow.run(
            user_input=request.query,
            query_for_classification=full_context_query,  # Pass full context
            user_profile=user_profile_raw,  # Pass profile for potential updates
            conversation_history=history_context,  # Pass conversation history
            user_location=user_location_tuple,
            response_language=response_language  # Tell workflow what language to respond in
        )
        
        logger.info(f"📊 [BACKEND STEP 4] Workflow result keys: {list(result.keys())}")
        logger.info(f"   - Has 'nearby_hospitals': {'nearby_hospitals' in result}")
        if 'nearby_hospitals' in result:
            logger.info(f"   - nearby_hospitals type: {type(result['nearby_hospitals'])}")
            logger.info(f"   - nearby_hospitals length: {len(result['nearby_hospitals']) if result['nearby_hospitals'] else 0}")
            if result['nearby_hospitals']:
                logger.info(f"   - First hospital: {result['nearby_hospitals'][0]}")
        
        # Process response with DISHA compliance
        try:
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
        except Exception as compliance_error:
            logger.error(f"Compliance processing failed: {compliance_error}")
            # Create minimal compliant response to continue
            compliant_response = {
                'blockchain_audit': None,
                'response': {}
            }
        
        # Check if workflow updated the profile
        if result.get("profile_updated"):
            # Encrypt updated data before storing in users collection
            update_fields = {}
            
            if user_profile_raw.get("age"):
                encrypted_age = encryption_manager.encrypt(str(user_profile_raw["age"]), user_salt)
                update_fields["age_encrypted"] = encrypted_age
            
            if user_profile_raw.get("gender"):
                encrypted_gender = encryption_manager.encrypt(user_profile_raw["gender"], user_salt)
                update_fields["gender_encrypted"] = encrypted_gender
            
            if user_profile_raw.get("medical_history"):
                encrypted_history = encryption_manager.encrypt(user_profile_raw["medical_history"], user_salt)
                update_fields["medical_history_encrypted"] = encrypted_history
            
            if user_profile_raw.get("medications"):
                encrypted_meds = encryption_manager.encrypt(user_profile_raw["medications"], user_salt)
                update_fields["medications_encrypted"] = encrypted_meds
            
            if update_fields:
                await mongodb_manager.db.users.update_one(
                    {"_id": user_id},
                    {"$set": update_fields}
                )
                logger.info(f"Updated user profile for {user_id}")
        
        # --- TTS AUDIO GENERATION (if requested) ---
        audio_url = None
        if request.generate_audio:
            from openai import OpenAI
            import hashlib
            import re
            
            # Use primary OpenAI key for TTS
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY_1"))
            
            # Get text to speak
            raw_output = result.get("output") if isinstance(result, dict) else result
            tts_input = raw_output if isinstance(raw_output, str) else str(raw_output)
            
            # Clean text for TTS (but keep in displayed text)
            # Remove citations
            tts_input = re.sub(r'\[Source:.*?\]', '', tts_input)
            tts_input = re.sub(r'\[\d+\]', '', tts_input)
            tts_input = re.sub(r'\[Citation:.*?\]', '', tts_input)
            
            # Remove markdown formatting
            tts_input = re.sub(r'#{1,6}\s*', '', tts_input)  # Headers (###)
            tts_input = re.sub(r'\*\*(.*?)\*\*', r'\1', tts_input)  # Bold
            tts_input = re.sub(r'\*(.*?)\*', r'\1', tts_input)  # Italic
            tts_input = re.sub(r'`(.*?)`', r'\1', tts_input)  # Inline code
            tts_input = re.sub(r'^\s*[-*+]\s+', '', tts_input, flags=re.MULTILINE)  # List markers
            tts_input = re.sub(r'^\s*\d+\.\s+', '', tts_input, flags=re.MULTILINE)  # Numbered lists
            
            # Remove emojis (all Unicode emoji characters)
            tts_input = re.sub(r'[^\w\s,.!?;:()\-\'/"]', '', tts_input)
            
            # Clean up multiple spaces and newlines
            tts_input = re.sub(r'\n+', '. ', tts_input)  # Replace newlines with periods
            tts_input = re.sub(r'\s+', ' ', tts_input).strip()
            
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
        response_data = {
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
        
        logger.info(f"✅ Sending response for session {session_id}: {len(str(response_data))} chars")
        return response_data
        
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


# ==================== DOCUMENT UPLOAD ENDPOINTS ====================

@app.post("/documents/upload")
async def upload_medical_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and extract medical document (PDF)"""
    import tempfile
    from pathlib import Path
    from src.document_processor.pdf_extractor import MedicalDocumentExtractor
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported"
        )
    
    try:
        user_id = current_user["_id"]
        user_salt = current_user["encryption_key_id"]
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        # Extract and analyze
        extractor = MedicalDocumentExtractor(llm=config.llm_secondary)
        result = extractor.process_medical_pdf(tmp_path)
        
        # Determine status - always "processed" if text was extracted
        # Analysis can fail but document is still uploaded
        doc_status = "processed"
        if not result.get("success"):
            doc_status = "extraction_failed"
        elif result.get("analysis", {}).get("error"):
            doc_status = "processed"  # Text extracted, analysis failed (non-critical)
        
        # Store in MongoDB
        document_doc = {
            "user_id": user_id,
            "file_name": file.filename,
            "file_size": len(content),
            "upload_date": datetime.utcnow(),
            "extraction": {
                "num_pages": result.get("num_pages"),
                "extracted_at": result.get("extracted_at")
            },
            "analysis": result.get("analysis", {}),
            # Encrypt full text
            "full_text_encrypted": encryption_manager.encrypt(
                result.get("full_text", ""), 
                user_salt
            ) if result.get("full_text") else None,
            "status": doc_status,
            "error": result.get("error")
        }
        
        insert_result = await mongodb_manager.db.user_documents.insert_one(document_doc)
        document_id = str(insert_result.inserted_id)
        
        # Cleanup temp file
        os.unlink(tmp_path)
        
        # Build user-friendly message
        message = "Document uploaded successfully"
        if result.get("analysis", {}).get("error"):
            message += " (detailed analysis pending)"
        
        logger.info(f"📄 Document uploaded: {file.filename} for user {user_id} - Status: {doc_status}")
        
        # Check if document belongs to user and update profile
        profile_updated = False
        ownership_status = "unknown"
        
        analysis = result.get("analysis", {})
        if analysis.get("analyzed") and analysis.get("patient_name"):
            # Get user's display name
            user_email = encryption_manager.decrypt(current_user.get("email_encrypted", ""), user_salt)
            user_display_name = current_user.get("display_name", "")
            
            # Simple name matching (case insensitive, partial match)
            patient_name = analysis.get("patient_name", "").lower()
            
            # Check if patient name matches user
            name_match = False
            if user_display_name:
                name_parts = user_display_name.lower().split()
                # Match if any part of display name is in patient name
                name_match = any(part in patient_name for part in name_parts if len(part) > 2)
            
            if name_match:
                ownership_status = "confirmed_user"
                # Update user profile with document data
                try:
                    import json
                    update_fields = {}
                    
                    # Add new medications
                    if analysis.get("medications"):
                        current_meds = current_user.get("medications_encrypted")
                        if current_meds:
                            existing = json.loads(encryption_manager.decrypt(current_meds, user_salt))
                        else:
                            existing = []
                        
                        for med in analysis["medications"]:
                            if med not in existing:
                                existing.append(med)
                        
                        update_fields["medications_encrypted"] = encryption_manager.encrypt(
                            json.dumps(existing), user_salt
                        )
                    
                    # Add new diagnoses to medical history
                    if analysis.get("diagnoses"):
                        current_history = current_user.get("medical_history_encrypted")
                        if current_history:
                            existing = json.loads(encryption_manager.decrypt(current_history, user_salt))
                        else:
                            existing = []
                        
                        for diagnosis in analysis["diagnoses"]:
                            if diagnosis not in existing:
                                existing.append(diagnosis)
                        
                        update_fields["medical_history_encrypted"] = encryption_manager.encrypt(
                            json.dumps(existing), user_salt
                        )
                    
                    # Update user document
                    if update_fields:
                        await mongodb_manager.db.users.update_one(
                            {"_id": user_id},
                            {"$set": update_fields}
                        )
                        profile_updated = True
                        logger.info(f"✅ Profile updated from document for user {user_id}")
                        message += " | Profile updated with medications and diagnoses"
                
                except Exception as e:
                    logger.error(f"Failed to update profile from document: {e}")
            else:
                ownership_status = "different_patient"
                logger.info(f"⚠️ Document patient name '{patient_name}' doesn't match user '{user_display_name}'")
        
        return {
            "success": True,
            "document_id": document_id,
            "file_name": file.filename,
            "num_pages": result.get("num_pages"),
            "analysis": result.get("analysis", {}),
            "message": message,
            "profile_updated": profile_updated,
            "ownership_status": ownership_status
        }
        
    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def get_user_documents(
    current_user: dict = Depends(get_current_user)
):
    """Get all documents for current user"""
    try:
        user_id = current_user["_id"]
        
        documents = await mongodb_manager.db.user_documents.find(
            {"user_id": user_id}
        ).sort("upload_date", -1).to_list(length=50)
        
        # Format response (without encrypted content)
        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "id": str(doc["_id"]),
                "file_name": doc["file_name"],
                "file_size": doc["file_size"],
                "upload_date": doc["upload_date"].isoformat(),
                "num_pages": doc.get("extraction", {}).get("num_pages"),
                "status": doc.get("status"),
                "analysis": doc.get("analysis", {})
            })
        
        return {"documents": formatted_docs}
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user's document"""
    try:
        user_id = current_user["_id"]
        
        result = await mongodb_manager.db.user_documents.delete_one({
            "_id": ObjectId(document_id),
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"🗑️ Document deleted: {document_id}")
        return {"success": True, "message": "Document deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
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
        if not blockchain_logger:
            raise HTTPException(status_code=503, detail="Blockchain service unavailable")
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
        if not blockchain_logger:
            raise HTTPException(status_code=503, detail="Blockchain service unavailable")
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
