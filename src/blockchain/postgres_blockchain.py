"""
Cloud PostgreSQL Blockchain Implementation
Shared blockchain across multiple developers/environments
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import os

logger = logging.getLogger(__name__)


class PostgresBlockchain:
    """
    PostgreSQL-based blockchain for cloud deployment
    - Shared across multiple environments
    - Same features as SQLite version
    - Production-ready with connection pooling
    """
    
    def __init__(self, connection_url: str = None):
        self.connection_url = connection_url or os.getenv("BLOCKCHAIN_DATABASE_URL")
        if not self.connection_url:
            raise ValueError("BLOCKCHAIN_DATABASE_URL not set")
        
        self._init_database()
        logger.info(f"✅ Cloud blockchain initialized")
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_url)
    
    def _init_database(self):
        """Initialize blockchain tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create blocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                block_number SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                previous_hash TEXT NOT NULL,
                block_hash TEXT NOT NULL UNIQUE,
                data TEXT NOT NULL,
                nonce INTEGER NOT NULL
            )
        ''')
        
        # Create audit logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                block_number INTEGER NOT NULL,
                anonymous_id TEXT NOT NULL,
                action TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                metadata TEXT,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (block_number) REFERENCES blocks(block_number)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_anonymous_id ON audit_logs(anonymous_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action ON audit_logs(action)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)')
        
        conn.commit()
        
        # Create genesis block if doesn't exist
        cursor.execute('SELECT COUNT(*) FROM blocks')
        if cursor.fetchone()[0] == 0:
            self._create_genesis_block(conn)
        
        cursor.close()
        conn.close()
    
    def _create_genesis_block(self, conn):
        """Create the first block"""
        cursor = conn.cursor()
        genesis_data = {
            "type": "GENESIS",
            "message": "Pran Protocol Private Blockchain Genesis Block",
            "timestamp": datetime.now().isoformat()
        }
        
        genesis_hash = hashlib.sha256(json.dumps(genesis_data).encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO blocks (timestamp, previous_hash, block_hash, data, nonce)
            VALUES (%s, %s, %s, %s, %s)
        ''', (datetime.now(), "0" * 64, genesis_hash, json.dumps(genesis_data), 0))
        
        conn.commit()
        logger.info("🎉 Genesis block created")
    
    def _calculate_hash(self, block_number: int, timestamp: str, previous_hash: str, 
                       data: str, nonce: int) -> str:
        """Calculate block hash"""
        block_string = f"{block_number}{timestamp}{previous_hash}{data}{nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def _mine_block(self, block_number: int, timestamp: str, previous_hash: str, 
                    data: str, difficulty: int = 2) -> tuple:
        """Mine a new block (Proof of Work)"""
        nonce = 0
        target = "0" * difficulty
        
        while True:
            block_hash = self._calculate_hash(block_number, timestamp, previous_hash, data, nonce)
            if block_hash.startswith(target):
                return block_hash, nonce
            nonce += 1
            
            if nonce % 100000 == 0:
                logger.debug(f"Mining... nonce={nonce}")
    
    def log_audit(self, anonymous_id: str, action: str, metadata: Dict[str, Any] = None) -> Optional[Dict]:
        """Log an audit event to the blockchain"""
        try:
            # Fix: action might be a dict, convert to string
            if isinstance(action, dict):
                action = json.dumps(action)
            
            # Ensure metadata is JSON-serializable
            if metadata:
                try:
                    metadata_json = json.dumps(metadata, default=str)
                except Exception as e:
                    logger.error(f"❌ Failed to serialize metadata: {e}")
                    metadata_json = json.dumps({"error": "serialization_failed"})
            else:
                metadata_json = None
            
            logger.info(f"🔌 Connecting to database...")
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            logger.info(f"   ✓ Connected")
            
            # Get last block
            logger.info(f"📦 Fetching last block...")
            cursor.execute('SELECT * FROM blocks ORDER BY block_number DESC LIMIT 1')
            last_block = cursor.fetchone()
            
            if not last_block:
                logger.error(f"   ❌ No genesis block found")
                cursor.close()
                conn.close()
                return None
            
            logger.info(f"   ✓ Last block: #{last_block['block_number']}")
            
            # Create new block
            block_number = last_block['block_number'] + 1
            timestamp = datetime.now().isoformat()
            previous_hash = last_block['block_hash']
            
            # Create audit data (use simplified metadata for block data)
            audit_data = {
                "anonymous_id": anonymous_id,
                "action": action,
                "timestamp": timestamp
            }
            
            data = json.dumps(audit_data)
            data_hash = hashlib.sha256(data.encode()).hexdigest()
            logger.info(f"⛏️  Mining block #{block_number}...")
            
            # Mine block
            block_hash, nonce = self._mine_block(block_number, timestamp, previous_hash, data)
            logger.info(f"   ✓ Block mined: {block_hash[:16]}...")
            
            # Insert block
            logger.info(f"💾 Inserting block into database...")
            logger.info(f"   Parameters: timestamp={type(datetime.now())}, prev_hash={type(previous_hash)}, block_hash={type(block_hash)}, data={type(data)}, nonce={type(nonce)}")
            cursor.execute('''
                INSERT INTO blocks (timestamp, previous_hash, block_hash, data, nonce)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING block_number
            ''', (datetime.now(), previous_hash, block_hash, data, nonce))
            
            new_block_number = cursor.fetchone()['block_number']
            logger.info(f"   ✓ Block inserted: #{new_block_number}")
            
            # Insert audit log with metadata as TEXT
            cursor.execute('''
                INSERT INTO audit_logs 
                (block_number, anonymous_id, action, data_hash, metadata, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (new_block_number, anonymous_id, action, data_hash, metadata_json, datetime.now()))
            logger.info(f"   ✓ Audit log inserted")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            result = {
                "tx_hash": block_hash,
                "block_number": new_block_number,
                "timestamp": timestamp,
                "status": "success"
            }
            
            logger.info(f"✅ Audit logged to cloud blockchain: Block #{new_block_number}, TX: {block_hash[:10]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Cloud blockchain audit failed: {e}")
            logger.error(f"   Exception type: {type(e)}")
            logger.error(f"   Exception args: {e.args}")
            import traceback
            logger.error(f"   Full traceback:\n{traceback.format_exc()}")
            if conn:
                conn.rollback()
                conn.close()
            return None
    
    def get_audit_trail(self, anonymous_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a user"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute('''
            SELECT a.*, b.block_hash, b.previous_hash, b.nonce
            FROM audit_logs a
            JOIN blocks b ON a.block_number = b.block_number
            WHERE a.anonymous_id = %s
            ORDER BY a.timestamp DESC
        ''', (anonymous_id,))
        
        results = cursor.fetchall()
        
        # Convert to list of dicts and parse JSON fields
        records = []
        for row in results:
            record = dict(row)
            record['timestamp'] = record['timestamp'].isoformat() if record.get('timestamp') else None
            # Parse metadata from JSON string to dict
            if record.get('metadata'):
                try:
                    record['metadata'] = json.loads(record['metadata'])
                except:
                    record['metadata'] = {}
            records.append(record)
        
        cursor.close()
        conn.close()
        return records
    
    def verify_chain_integrity(self) -> bool:
        """Verify the entire blockchain hasn't been tampered with"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute('SELECT * FROM blocks ORDER BY block_number ASC')
        blocks = cursor.fetchall()
        
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i-1]
            
            # Verify previous hash links
            if current['previous_hash'] != previous['block_hash']:
                logger.error(f"❌ Chain broken at block {current['block_number']}")
                cursor.close()
                conn.close()
                return False
            
            # Verify block hash
            calculated_hash = self._calculate_hash(
                current['block_number'],
                current['timestamp'].isoformat(),
                current['previous_hash'],
                current['data'],
                current['nonce']
            )
            
            if calculated_hash != current['block_hash']:
                logger.error(f"❌ Block {current['block_number']} hash invalid")
                cursor.close()
                conn.close()
                return False
        
        cursor.close()
        conn.close()
        logger.info("✅ Blockchain integrity verified")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total blocks
        cursor.execute('SELECT COUNT(*) as count FROM blocks')
        total_blocks = cursor.fetchone()['count']
        
        # Total audits
        cursor.execute('SELECT COUNT(*) as count FROM audit_logs')
        total_audits = cursor.fetchone()['count']
        
        # Unique users
        cursor.execute('SELECT COUNT(DISTINCT anonymous_id) as count FROM audit_logs')
        unique_users = cursor.fetchone()['count']
        
        # Action breakdown
        cursor.execute('SELECT action, COUNT(*) as count FROM audit_logs GROUP BY action')
        actions = cursor.fetchall()
        actions_breakdown = {row['action']: row['count'] for row in actions}
        
        cursor.close()
        conn.close()
        
        return {
            "total_blocks": total_blocks,
            "total_audits": total_audits,
            "unique_users": unique_users,
            "actions_breakdown": actions_breakdown,
            "chain_integrity": self.verify_chain_integrity()
        }


class PostgresBlockchainAuditLogger:
    """Adapter for DISHAComplianceManager compatibility"""
    
    def __init__(self, connection_url: str = None):
        self.blockchain = PostgresBlockchain(connection_url)
        self.enabled = True
        logger.info("✅ Cloud PostgreSQL blockchain audit logger initialized")
    
    async def log_action(self, user_id: str = None, anonymous_id: str = None, 
                        action: str = None, data: Dict[str, Any] = None,
                        metadata: Dict[str, Any] = None) -> Optional[Dict]:
        """Log action to cloud blockchain (async wrapper)"""
        logger.info(f"🔵 PostgresBlockchainAuditLogger.log_action called")
        logger.info(f"   user_id={user_id} (type: {type(user_id)})")
        logger.info(f"   anonymous_id={anonymous_id} (type: {type(anonymous_id)})")
        logger.info(f"   action={action} (type: {type(action)})")
        logger.info(f"   data={type(data)}, keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        logger.info(f"   metadata={type(metadata)}, keys={list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
        
        if not self.enabled:
            return None
        
        # Support both parameter styles (user_id or anonymous_id)
        anon_id = user_id or anonymous_id
        meta = data or metadata or {}
        
        logger.info(f"   → Calling blockchain.log_audit({anon_id}, {action}, {type(meta)})")
        return self.blockchain.log_audit(anon_id, action, meta)
    
    def get_audit_trail(self, anonymous_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for user"""
        return self.blockchain.get_audit_trail(anonymous_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        return self.blockchain.get_statistics()
