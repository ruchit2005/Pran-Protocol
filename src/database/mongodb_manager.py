# MongoDB Connection Manager
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MongoDBManager:
    """MongoDB Atlas connection manager"""
    
    def __init__(self, connection_uri: str, database_name: str):
        self.connection_uri = connection_uri
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                self.connection_uri,
                serverSelectionTimeoutMS=5000
            )
            # Verify connection
            await self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            logger.info(f"✅ Connected to MongoDB: {self.database_name}")
            
            # Create indexes for performance
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Users collection - firebase_uid is indexed but not unique (allows multiple nulls)
            await self.db.users.create_index("firebase_uid", sparse=True)
            await self.db.users.create_index("blockchain_identity")
            
            # Sessions collection
            await self.db.sessions.create_index([("user_id", 1), ("created_at", -1)])
            await self.db.sessions.create_index("blockchain_session_hash")
            
            # Messages collection
            await self.db.messages.create_index([("session_id", 1), ("timestamp", 1)])
            await self.db.messages.create_index("blockchain_tx_hash")
            
            # Audit logs collection
            await self.db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
            await self.db.audit_logs.create_index("action")
            
            # Encryption keys
            await self.db.encryption_keys.create_index("key_id", unique=True)
            await self.db.encryption_keys.create_index("status")
            
            # Blockchain records
            await self.db.blockchain_records.create_index("blockchain_tx_hash", unique=True)
            await self.db.blockchain_records.create_index([("verified", 1), ("timestamp", -1)])
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {e}")
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """Get a collection"""
        return self.db[collection_name]


# Global instance
mongodb_manager = MongoDBManager(
    connection_uri=os.getenv("MONGODB_URI", ""),
    database_name=os.getenv("MONGODB_DB_NAME", "pran-protocol")
)
