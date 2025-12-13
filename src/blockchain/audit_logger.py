# Blockchain Audit Logger
from web3 import Web3
import hashlib
import json
import os
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BlockchainAuditLogger:
    """
    Immutable audit logging using blockchain
    Supports Ethereum, Polygon, or private networks
    """
    
    def __init__(
        self,
        provider_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        """
        Initialize blockchain connection
        
        Args:
            provider_url: Blockchain RPC endpoint
            contract_address: Deployed smart contract address
            private_key: Account private key for signing transactions
        """
        self.provider_url = provider_url or os.getenv("BLOCKCHAIN_PROVIDER_URL")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        self.private_key = private_key or os.getenv("BLOCKCHAIN_PRIVATE_KEY")
        
        if not all([self.provider_url, self.contract_address, self.private_key]):
            logger.warning("⚠️ Blockchain not configured. Audit logging disabled.")
            self.enabled = False
            return
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
            
            if not self.w3.is_connected():
                raise ConnectionError("Failed to connect to blockchain")
            
            self.account = self.w3.eth.account.from_key(self.private_key)
            
            # Load contract ABI
            contract_abi = self._load_contract_abi()
            self.contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            self.enabled = True
            logger.info(f"✅ Blockchain audit logger connected: {self.w3.eth.chain_id}")
            logger.info(f"   Account: {self.account.address}")
            
        except Exception as e:
            logger.error(f"❌ Blockchain initialization failed: {e}")
            self.enabled = False
    
    def _load_contract_abi(self) -> list:
        """Load smart contract ABI"""
        # Event-based audit contract ABI
        return [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "user", "type": "address"},
                    {"indexed": False, "name": "action", "type": "string"},
                    {"indexed": False, "name": "dataHash", "type": "bytes32"},
                    {"indexed": False, "name": "timestamp", "type": "uint256"}
                ],
                "name": "AuditLog",
                "type": "event"
            },
            {
                "inputs": [
                    {"name": "action", "type": "string"},
                    {"name": "dataHash", "type": "bytes32"}
                ],
                "name": "logAudit",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def hash_data(self, data: Dict[str, Any]) -> str:
        """Create SHA-256 hash of data"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Log an action to the blockchain
        
        Args:
            user_id: User identifier
            action: Action type (READ, WRITE, UPDATE, DELETE, etc.)
            data: Data being acted upon
            
        Returns:
            Dict with transaction hash and block number, or None if disabled
        """
        if not self.enabled:
            logger.debug("Blockchain logging disabled, skipping")
            return None
        
        try:
            # Create data hash
            data_hash = self.hash_data({
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                **data
            })
            data_hash_bytes = bytes.fromhex(data_hash)
            
            # Build transaction
            tx = self.contract.functions.logAudit(
                action,
                data_hash_bytes
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 500000,  # Increased from 200,000 to handle complex contracts
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            result = {
                "tx_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"✅ Blockchain audit logged: {action} - TX: {result['tx_hash'][:10]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Blockchain logging failed: {e}")
            return None
    
    def verify_data(
        self,
        record_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Verify data integrity against blockchain record
        
        Args:
            record_id: Blockchain record ID
            data: Data to verify
            
        Returns:
            True if data matches blockchain record
        """
        if not self.enabled:
            return False
        
        try:
            # Create hash of current data
            data_hash = self.hash_data(data)
            data_hash_bytes = bytes.fromhex(data_hash)
            record_id_bytes = bytes.fromhex(record_id)
            
            # Call contract to verify
            is_valid = self.contract.functions.verifyRecord(
                record_id_bytes,
                data_hash_bytes
            ).call()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    def get_gas_price(self) -> int:
        """Get current gas price in wei"""
        if self.enabled:
            return self.w3.eth.gas_price
        return 0
    
    def estimate_cost(self) -> Dict[str, float]:
        """Estimate cost per transaction"""
        if not self.enabled:
            return {"eth": 0, "usd": 0}
        
        gas_price = self.w3.eth.gas_price
        gas_limit = 200000
        cost_wei = gas_price * gas_limit
        cost_eth = self.w3.from_wei(cost_wei, 'ether')
        
        # Note: You'd need to integrate with a price API for USD conversion
        return {
            "gas_price_gwei": self.w3.from_wei(gas_price, 'gwei'),
            "estimated_eth": float(cost_eth),
            "gas_limit": gas_limit
        }


# Singleton instance
blockchain_logger = BlockchainAuditLogger()
