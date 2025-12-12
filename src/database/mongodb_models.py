# Database Models for MongoDB
from datetime import datetime
from typing import Optional, List, Any, Annotated
from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer
from bson import ObjectId

def validate_object_id(v: Any) -> ObjectId:
    """Validate ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")

# Annotated type for ObjectId with Pydantic v2
PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str)
]


class ConsentAgreement(BaseModel):
    """HIPAA consent tracking"""
    type: str  # "HIPAA", "Privacy Policy", "Terms of Service"
    version: str
    accepted_at: datetime
    ip_address: str


class UserMongo(BaseModel):
    """User model with encryption support"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    firebase_uid: Optional[str] = None
    email_encrypted: str  # AES-256 encrypted
    display_name_encrypted: Optional[str] = None
    photo_url: Optional[str] = None  # Not PHI, can be plain
    encryption_key_id: str  # Reference to encryption key
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    mfa_enabled: bool = False
    consent_agreements: List[ConsentAgreement] = []
    blockchain_identity: Optional[str] = None  # Public key
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class SessionMongo(BaseModel):
    """Chat session with blockchain link"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    user_id: PyObjectId
    title_encrypted: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # "active", "archived"
    blockchain_session_hash: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class MessageMongo(BaseModel):
    """Encrypted message with blockchain proof"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    session_id: PyObjectId
    user_id: PyObjectId
    role: str  # "user", "assistant"
    content_encrypted: str  # AES-256 encrypted
    intent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address_hashed: str  # SHA-256 for audit
    blockchain_tx_hash: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class BlockchainProof(BaseModel):
    """Blockchain verification proof"""
    tx_hash: str
    block_number: int
    verified: bool


class UserProfileMongo(BaseModel):
    """User health profile for personalized recommendations"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    user_id: PyObjectId
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: str = "[]"  # JSON string of conditions
    allergies: str = "[]"         # JSON string of allergies
    medications: str = "[]"       # JSON string of current medications
    language_preference: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AuditLogMongo(BaseModel):
    """Comprehensive audit log"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    user_id: PyObjectId
    action: str  # "READ", "WRITE", "UPDATE", "DELETE", "LOGIN", "EXPORT"
    resource_type: str  # "message", "session", "profile"
    resource_id: Optional[PyObjectId] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address_hashed: str
    user_agent: str
    result: str  # "success", "failure"
    blockchain_proof: Optional[BlockchainProof] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class EncryptionKey(BaseModel):
    """Key management"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    key_id: str  # Unique identifier
    encrypted_key: str  # Encrypted with master key
    algorithm: str = "AES-256-GCM"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    rotated_at: Optional[datetime] = None
    status: str = "active"  # "active", "rotated", "revoked"
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class BlockchainRecord(BaseModel):
    """Blockchain sync record"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    record_type: str  # "user_action", "data_modification"
    data_hash: str  # SHA-256
    blockchain_tx_hash: str
    block_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False
    verification_attempts: int = 0
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
