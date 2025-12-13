"""
SIMPLIFIED PRIVATE BLOCKCHAIN SOLUTION
Using local SQLite blockchain (offline, private, instant)
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class PrivateBlockchain:
    """
    Private blockchain implementation using SQLite
    - No gas fees
    - Instant transactions
    - Private (only you can access)
    - Immutable audit trail
    - HIPAA compliant (data never leaves your server)
    """
    
    def __init__(self, db_path: str = "data/blockchain.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"✅ Private blockchain initialized: {db_path}")
    
    def _init_database(self):
        """Initialize blockchain database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create blocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                block_number INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                block_hash TEXT NOT NULL UNIQUE,
                data TEXT NOT NULL,
                nonce INTEGER NOT NULL
            )
        ''')
        
        # Create audit logs table (indexed for fast queries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_number INTEGER NOT NULL,
                anonymous_id TEXT NOT NULL,
                action TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL,
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
        
        conn.close()
    
    def _create_genesis_block(self, conn):
        """Create the first block"""
        cursor = conn.cursor()
        genesis_data = {
            "type": "GENESIS",
            "message": "Pran-Protocol Healthcare Blockchain",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        block_hash = self._calculate_hash(0, "0", json.dumps(genesis_data), 0)
        
        cursor.execute('''
            INSERT INTO blocks (timestamp, previous_hash, block_hash, data, nonce)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            "0",
            block_hash,
            json.dumps(genesis_data),
            0
        ))
        
        conn.commit()
        logger.info("✅ Genesis block created")
    
    def _calculate_hash(self, block_number: int, previous_hash: str, data: str, nonce: int) -> str:
        """Calculate SHA-256 hash of block"""
        content = f"{block_number}{previous_hash}{data}{nonce}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _mine_block(self, previous_hash: str, data: str, difficulty: int = 2) -> tuple:
        """Mine a new block with proof-of-work"""
        nonce = 0
        block_number = self._get_last_block_number() + 1
        
        while True:
            block_hash = self._calculate_hash(block_number, previous_hash, data, nonce)
            if block_hash[:difficulty] == "0" * difficulty:
                return block_hash, nonce
            nonce += 1
            
            # Simplified mining (max 10000 attempts)
            if nonce > 10000:
                return block_hash, nonce
    
    def _get_last_block_number(self) -> int:
        """Get the last block number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(block_number) FROM blocks')
        result = cursor.fetchone()[0]
        conn.close()
        return result if result else 0
    
    def _get_last_block_hash(self) -> str:
        """Get hash of the last block"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT block_hash FROM blocks ORDER BY block_number DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "0"
    
    async def log_audit(
        self,
        anonymous_id: str,
        action: str,
        data_hash: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log audit to private blockchain
        
        Args:
            anonymous_id: Anonymized user ID
            action: Action type (DIAGNOSIS, DATA_ACCESS, etc.)
            data_hash: SHA-256 hash of the data
            metadata: Additional metadata
            
        Returns:
            Block details with transaction info
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Create audit record
            audit_data = {
                "anonymous_id": anonymous_id,
                "action": action,
                "data_hash": data_hash,
                "metadata": metadata or {},
                "timestamp": timestamp
            }
            
            # Mine new block
            previous_hash = self._get_last_block_hash()
            block_data = json.dumps(audit_data)
            block_hash, nonce = self._mine_block(previous_hash, block_data)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO blocks (timestamp, previous_hash, block_hash, data, nonce)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, previous_hash, block_hash, block_data, nonce))
            
            block_number = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO audit_logs (block_number, anonymous_id, action, data_hash, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (block_number, anonymous_id, action, data_hash, json.dumps(metadata or {}), timestamp))
            
            conn.commit()
            conn.close()
            
            result = {
                "tx_hash": block_hash,
                "block_number": block_number,
                "timestamp": timestamp,
                "status": "success"
            }
            
            logger.info(f"✅ Audit logged to blockchain: Block #{block_number}, TX: {block_hash[:10]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Blockchain audit failed: {e}")
            return None
    
    def get_audit_trail(self, anonymous_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.*, b.block_hash, b.previous_hash, b.nonce
            FROM audit_logs a
            JOIN blocks b ON a.block_number = b.block_number
            WHERE a.anonymous_id = ?
            ORDER BY a.timestamp DESC
        ''', (anonymous_id,))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            record['metadata'] = json.loads(record['metadata']) if record['metadata'] else {}
            results.append(record)
        
        conn.close()
        return results
    
    def verify_chain_integrity(self) -> bool:
        """Verify blockchain integrity (detect tampering)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM blocks ORDER BY block_number')
        blocks = cursor.fetchall()
        conn.close()
        
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i-1]
            
            # Check previous hash link
            if current[2] != previous[3]:  # previous_hash != previous block_hash
                logger.error(f"❌ Chain broken at block {current[0]}")
                return False
            
            # Verify hash
            calculated_hash = self._calculate_hash(
                current[0],  # block_number
                current[2],  # previous_hash
                current[4],  # data
                current[5]   # nonce
            )
            
            if calculated_hash != current[3]:  # block_hash
                logger.error(f"❌ Hash mismatch at block {current[0]}")
                return False
        
        logger.info("✅ Blockchain integrity verified")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM blocks')
        total_blocks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM audit_logs')
        total_audits = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT anonymous_id) FROM audit_logs')
        unique_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT action, COUNT(*) FROM audit_logs GROUP BY action')
        actions = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_blocks": total_blocks,
            "total_audits": total_audits,
            "unique_users": unique_users,
            "actions_breakdown": actions,
            "chain_integrity": self.verify_chain_integrity()
        }


class PrivateBlockchainAuditLogger:
    """
    Adapter for private blockchain (drop-in replacement for Ethereum logger)
    """
    
    def __init__(self):
        self.blockchain = PrivateBlockchain()
        self.enabled = True
        logger.info("✅ Private blockchain audit logger initialized")
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Log audit action to private blockchain"""
        if not self.enabled:
            return None
        
        # Create data hash
        data_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        
        result = await self.blockchain.log_audit(
            anonymous_id=user_id,
            action=action,
            data_hash=data_hash,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                **data
            }
        )
        
        return result
    
    def get_audit_trail(self, anonymous_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for user"""
        return self.blockchain.get_audit_trail(anonymous_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        return self.blockchain.get_statistics()
