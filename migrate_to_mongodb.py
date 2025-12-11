# Migration Script: SQLite to MongoDB with Encryption
import asyncio
import sqlite3
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb_manager import mongodb_manager
from src.database.mongodb_models import UserMongo, SessionMongo, MessageMongo, AuditLogMongo
from src.security.encryption import PHIEncryptionManager
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLiteToMongoMigration:
    """Migrate data from SQLite to MongoDB with encryption"""
    
    def __init__(self, sqlite_db_path: str):
        self.sqlite_db_path = sqlite_db_path
        self.encryption_manager = PHIEncryptionManager()
        self.user_mapping = {}  # SQLite ID -> MongoDB ObjectId
        self.session_mapping = {}
        
    async def migrate(self):
        """Run full migration"""
        logger.info("=== Starting SQLite to MongoDB Migration ===\n")
        
        # Connect to MongoDB
        await mongodb_manager.connect()
        
        # Clear existing data (optional - ask user)
        logger.info("⚠️  This will clear existing MongoDB data!")
        logger.info("Collections to clear: users, sessions, messages, audit_logs")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            logger.info("❌ Migration cancelled")
            return
        
        # Clear collections and indexes
        await mongodb_manager.db.users.drop()
        await mongodb_manager.db.sessions.drop()
        await mongodb_manager.db.messages.drop()
        await mongodb_manager.db.audit_logs.drop()
        logger.info("✅ Cleared existing data and indexes")
        
        # Recreate indexes without the problematic firebase_uid unique constraint
        await mongodb_manager.db.users.create_index("blockchain_identity")
        await mongodb_manager.db.sessions.create_index([("user_id", 1), ("created_at", -1)])
        await mongodb_manager.db.messages.create_index([("session_id", 1), ("timestamp", 1)])
        await mongodb_manager.db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
        logger.info("✅ Recreated indexes\n")
        
        # Connect to SQLite
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Migrate in order due to foreign keys
            await self.migrate_users(conn)
            await self.migrate_sessions(conn)
            await self.migrate_messages(conn)
            
            logger.info("\n=== Migration Complete ===")
            logger.info(f"✅ Users migrated: {len(self.user_mapping)}")
            logger.info(f"✅ Sessions migrated: {len(self.session_mapping)}")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()
            await mongodb_manager.close()
    
    async def migrate_users(self, conn):
        """Migrate users table"""
        logger.info("📦 Migrating users...")
        
        cursor = conn.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        for user_row in users:
            # Generate encryption salt for this user
            user_salt = self.encryption_manager.generate_user_salt()
            
            # Encrypt email
            email_encrypted = self.encryption_manager.encrypt(
                user_row['email'],
                user_salt
            )
            
            # Encrypt display name if exists
            display_name_encrypted = None
            if user_row['display_name']:
                display_name_encrypted = self.encryption_manager.encrypt(
                    user_row['display_name'],
                    user_salt
                )
            
            # Create MongoDB user document
            user_doc = {
                "firebase_uid": user_row['firebase_uid'],
                "email_encrypted": email_encrypted,
                "display_name_encrypted": display_name_encrypted,
                "photo_url": user_row['photo_url'],
                "encryption_key_id": user_salt,  # Store salt as key_id for simplicity
                "created_at": datetime.fromisoformat(user_row['created_at']),
                "last_login": None,
                "mfa_enabled": False,
                "consent_agreements": [],
                "blockchain_identity": None
            }
            
            # Insert into MongoDB
            result = await mongodb_manager.db.users.insert_one(user_doc)
            
            # Map old ID to new ObjectId
            self.user_mapping[user_row['id']] = result.inserted_id
            
            logger.info(f"   ✓ Migrated user: {user_row['email']} -> {result.inserted_id}")
        
        logger.info(f"✅ Users migrated: {len(users)}\n")
    
    async def migrate_sessions(self, conn):
        """Migrate sessions table"""
        logger.info("📦 Migrating sessions...")
        
        try:
            cursor = conn.execute("SELECT * FROM sessions")
            sessions = cursor.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"   ⚠️ Table 'sessions' not found, skipping: {e}")
            return
        
        for session_row in sessions:
            # Get mapped user ID
            user_id = self.user_mapping.get(session_row['user_id'])
            if not user_id:
                logger.warning(f"   ⚠️ Skipping session {session_row['id']}: User not found")
                continue
            
            # Get user's encryption salt
            user_doc = await mongodb_manager.db.users.find_one({"_id": user_id})
            user_salt = user_doc['encryption_key_id']
            
            # Encrypt title
            title_encrypted = self.encryption_manager.encrypt(
                session_row['title'],
                user_salt
            )
            
            # Create MongoDB session document
            session_doc = {
                "user_id": user_id,
                "title_encrypted": title_encrypted,
                "created_at": datetime.fromisoformat(session_row['created_at']),
                "updated_at": datetime.utcnow(),
                "status": "active",
                "blockchain_session_hash": None
            }
            
            # Insert into MongoDB
            result = await mongodb_manager.db.sessions.insert_one(session_doc)
            
            # Map old ID to new ObjectId
            self.session_mapping[session_row['id']] = result.inserted_id
            
            logger.info(f"   ✓ Migrated session: {session_row['title'][:30]}...")
        
        logger.info(f"✅ Sessions migrated: {len(sessions)}\n")
    
    async def migrate_messages(self, conn):
        """Migrate messages table"""
        logger.info("📦 Migrating messages...")
        
        try:
            cursor = conn.execute("SELECT * FROM messages")
            messages = cursor.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"   ⚠️ Table 'messages' not found, skipping: {e}")
            return
        
        migrated_count = 0
        
        for msg_row in messages:
            # Get mapped session and user IDs
            session_id = self.session_mapping.get(msg_row['session_id'])
            if not session_id:
                logger.warning(f"   ⚠️ Skipping message: Session not found")
                continue
            
            # Get session to find user_id
            session_doc = await mongodb_manager.db.sessions.find_one({"_id": session_id})
            user_id = session_doc['user_id']
            
            # Get user's encryption salt
            user_doc = await mongodb_manager.db.users.find_one({"_id": user_id})
            user_salt = user_doc['encryption_key_id']
            
            # Encrypt message content
            content_encrypted = self.encryption_manager.encrypt(
                msg_row['content'],
                user_salt
            )
            
            # Hash IP address (dummy for migration)
            ip_hashed = self.encryption_manager.hash_for_audit("127.0.0.1")
            
            # Create MongoDB message document
            message_doc = {
                "session_id": session_id,
                "user_id": user_id,
                "role": msg_row['role'],
                "content_encrypted": content_encrypted,
                "intent": None,
                "timestamp": datetime.fromisoformat(msg_row['timestamp']),
                "ip_address_hashed": ip_hashed,
                "blockchain_tx_hash": None
            }
            
            # Insert into MongoDB
            await mongodb_manager.db.messages.insert_one(message_doc)
            migrated_count += 1
        
        logger.info(f"✅ Messages migrated: {migrated_count}\n")


async def main():
    """Main migration function"""
    sqlite_db_path = "healthcare.db"
    
    if not os.path.exists(sqlite_db_path):
        logger.error(f"❌ SQLite database not found: {sqlite_db_path}")
        return
    
    # Check environment variables
    if not os.getenv("MONGODB_URI"):
        logger.error("❌ MONGODB_URI not set in environment")
        return
    
    if not os.getenv("MASTER_ENCRYPTION_KEY"):
        logger.error("❌ MASTER_ENCRYPTION_KEY not set in environment")
        logger.info("Generate one using: python -m src.security.encryption")
        return
    
    migrator = SQLiteToMongoMigration(sqlite_db_path)
    await migrator.migrate()


if __name__ == "__main__":
    asyncio.run(main())
