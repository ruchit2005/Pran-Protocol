# MongoDB + Blockchain Integration Guide

## 🎯 Architecture Overview

### Data Flow with Security
```
User Query
    ↓
🔐 End-to-End Encryption (AES-256)
    ↓
MongoDB Atlas (Encrypted Storage)
    ↓
Blockchain Audit Log (Immutable Record)
    ↓
Smart Contract Verification
```

### HIPAA Compliance Requirements

1. **Data Encryption**
   - At rest: MongoDB encryption
   - In transit: TLS/SSL
   - Application level: AES-256 for PHI

2. **Access Control**
   - Role-based access (RBAC)
   - Multi-factor authentication
   - Audit logging of all access

3. **Audit Trail**
   - Immutable blockchain records
   - Who accessed what, when
   - All data modifications tracked

4. **Data Integrity**
   - Blockchain hash verification
   - Tamper-proof records
   - Digital signatures

## 🗄️ MongoDB Atlas Setup

### 1. Create MongoDB Atlas Account
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free M0 cluster (or paid for production)
3. Choose region close to your users
4. Enable **Encryption at Rest**

### 2. Configure Network Access
```
IP Whitelist: Add your application IPs
VPC Peering: For production (optional)
```

### 3. Create Database User
```
Username: pran-protocol-app
Password: <secure-password>
Role: readWrite on pran-protocol database
```

### 4. Get Connection String
```
mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/pran-protocol?retryWrites=true&w=majority
```

## 🔗 Blockchain Architecture

### Option 1: Private Ethereum Blockchain (Recommended for Healthcare)
**Pros:**
- Full control over network
- HIPAA compliant (private)
- Smart contracts for access control
- Gas-free for private network

**Tech Stack:**
- Hyperledger Besu / Quorum (Enterprise Ethereum)
- Web3.py for Python integration
- IPFS for storing encrypted documents
- Smart contracts for audit trail

### Option 2: Hyperledger Fabric (Healthcare-Specific)
**Pros:**
- Designed for enterprise/healthcare
- Permissioned blockchain
- Channels for privacy
- Used by healthcare orgs

**Tech Stack:**
- Hyperledger Fabric
- Chaincode (smart contracts)
- Fabric SDK for Python

### Option 3: Hybrid Approach (Best for MVP)
**Architecture:**
```
MongoDB Atlas (Primary Database)
    ↓
Hash all transactions
    ↓
Store hashes on blockchain (Ethereum/Polygon)
    ↓
Verify integrity on read
```

**Tech Stack:**
- MongoDB for data storage
- Web3.py for blockchain interaction
- Polygon/Mumbai testnet (low cost)
- SHA-256 hashing

## 📊 Database Schema Design

### MongoDB Collections

#### 1. **users** (Encrypted PHI)
```javascript
{
  _id: ObjectId,
  firebase_uid: String (indexed),
  email_encrypted: String,  // AES-256 encrypted
  display_name_encrypted: String,
  photo_url: String,  // Not PHI, can be plain
  encryption_key_id: String,  // Reference to key management
  created_at: ISODate,
  last_login: ISODate,
  mfa_enabled: Boolean,
  consent_agreements: [{
    type: String,  // "HIPAA", "Privacy Policy"
    version: String,
    accepted_at: ISODate,
    ip_address: String
  }],
  blockchain_identity: String  // Public key for verification
}
```

#### 2. **sessions** (Chat Sessions)
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  title_encrypted: String,
  created_at: ISODate,
  updated_at: ISODate,
  status: String,  // "active", "archived"
  blockchain_session_hash: String  // Links to blockchain record
}
```

#### 3. **messages** (Encrypted Content)
```javascript
{
  _id: ObjectId,
  session_id: ObjectId,
  user_id: ObjectId,
  role: String,  // "user", "assistant"
  content_encrypted: String,  // AES-256 encrypted PHI
  intent: String,
  timestamp: ISODate,
  ip_address_hashed: String,  // SHA-256 hash for audit
  blockchain_tx_hash: String  // Links to blockchain transaction
}
```

#### 4. **audit_logs** (Comprehensive Logging)
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  action: String,  // "READ", "WRITE", "UPDATE", "DELETE", "LOGIN", "EXPORT"
  resource_type: String,  // "message", "session", "profile"
  resource_id: ObjectId,
  timestamp: ISODate,
  ip_address_hashed: String,
  user_agent: String,
  result: String,  // "success", "failure"
  blockchain_proof: {
    tx_hash: String,
    block_number: Number,
    verified: Boolean
  }
}
```

#### 5. **encryption_keys** (Key Management)
```javascript
{
  _id: ObjectId,
  key_id: String (indexed, unique),
  encrypted_key: String,  // Encrypted with master key
  algorithm: String,  // "AES-256-GCM"
  created_at: ISODate,
  rotated_at: ISODate,
  status: String,  // "active", "rotated", "revoked"
}
```

#### 6. **blockchain_records** (Blockchain Sync)
```javascript
{
  _id: ObjectId,
  record_type: String,  // "user_action", "data_modification"
  data_hash: String,  // SHA-256 of original data
  blockchain_tx_hash: String,
  block_number: Number,
  timestamp: ISODate,
  verified: Boolean,
  verification_attempts: Number
}
```

## 🔐 Encryption Implementation

### 1. **Field-Level Encryption (MongoDB)**
```python
from pymongo import MongoClient
from pymongo.encryption import ClientEncryption
from pymongo.encryption_options import AutoEncryptionOpts

# Master key stored in AWS KMS, Azure Key Vault, or GCP KMS
kms_providers = {
    "aws": {
        "accessKeyId": os.getenv("AWS_ACCESS_KEY_ID"),
        "secretAccessKey": os.getenv("AWS_SECRET_ACCESS_KEY")
    }
}

# Automatic encryption for specified fields
auto_encryption_opts = AutoEncryptionOpts(
    kms_providers,
    "pran-protocol.__keyVault",
    schema_map=schema_map
)

client = MongoClient(MONGO_URI, auto_encryption_opts=auto_encryption_opts)
```

### 2. **Application-Level Encryption**
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class EncryptionManager:
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
    
    def encrypt_phi(self, data: str, user_salt: str) -> str:
        """Encrypt PHI with user-specific salt"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=user_salt.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    def decrypt_phi(self, encrypted_data: str, user_salt: str) -> str:
        """Decrypt PHI"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=user_salt.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()
```

## ⛓️ Blockchain Implementation

### Smart Contract (Solidity)
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HealthcareAudit {
    struct AuditRecord {
        address user;
        string action;
        bytes32 dataHash;
        uint256 timestamp;
        bool verified;
    }
    
    mapping(bytes32 => AuditRecord) public records;
    mapping(address => bytes32[]) public userRecords;
    
    event RecordCreated(
        bytes32 indexed recordId,
        address indexed user,
        string action,
        uint256 timestamp
    );
    
    function createRecord(
        string memory action,
        bytes32 dataHash
    ) public returns (bytes32) {
        bytes32 recordId = keccak256(
            abi.encodePacked(msg.sender, action, dataHash, block.timestamp)
        );
        
        records[recordId] = AuditRecord({
            user: msg.sender,
            action: action,
            dataHash: dataHash,
            timestamp: block.timestamp,
            verified: true
        });
        
        userRecords[msg.sender].push(recordId);
        
        emit RecordCreated(recordId, msg.sender, action, block.timestamp);
        
        return recordId;
    }
    
    function verifyRecord(bytes32 recordId, bytes32 dataHash) 
        public 
        view 
        returns (bool) 
    {
        return records[recordId].dataHash == dataHash;
    }
    
    function getUserRecords(address user) 
        public 
        view 
        returns (bytes32[] memory) 
    {
        return userRecords[user];
    }
}
```

### Python Integration (Web3.py)
```python
from web3 import Web3
import hashlib
import json

class BlockchainAuditLogger:
    def __init__(self, provider_url: str, contract_address: str, private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.account = self.w3.eth.account.from_key(private_key)
        
        with open('HealthcareAudit.json', 'r') as f:
            contract_abi = json.load(f)['abi']
        
        self.contract = self.w3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
    
    def log_action(self, user_id: str, action: str, data: dict) -> str:
        """Log action to blockchain"""
        # Hash the data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        data_hash_bytes = bytes.fromhex(data_hash)
        
        # Create transaction
        tx = self.contract.functions.createRecord(
            action,
            data_hash_bytes
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return receipt['transactionHash'].hex()
    
    def verify_data(self, record_id: str, data: dict) -> bool:
        """Verify data integrity against blockchain"""
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        data_hash_bytes = bytes.fromhex(data_hash)
        
        record_id_bytes = bytes.fromhex(record_id)
        
        return self.contract.functions.verifyRecord(
            record_id_bytes,
            data_hash_bytes
        ).call()
```

## 🔄 Migration Strategy

### Phase 1: Setup (Week 1)
1. Create MongoDB Atlas cluster
2. Deploy blockchain network (testnet first)
3. Implement encryption layer
4. Update environment variables

### Phase 2: Data Migration (Week 2)
1. Export SQLite data
2. Encrypt sensitive fields
3. Import to MongoDB
4. Create blockchain records for existing data

### Phase 3: Testing (Week 3)
1. Test encryption/decryption
2. Verify blockchain logging
3. Performance testing
4. Security audit

### Phase 4: Production (Week 4)
1. Deploy to production MongoDB
2. Deploy smart contracts to mainnet/private network
3. Enable monitoring and alerts
4. Train team on new system

## 📦 Dependencies to Add

```txt
# MongoDB
pymongo==4.6.1
motor==3.3.2  # Async MongoDB driver

# Encryption
cryptography==41.0.7
pycryptodome==3.19.0

# Blockchain
web3==6.11.3
eth-account==0.10.0
eth-utils==2.3.1

# Key Management (choose one)
boto3==1.34.10  # For AWS KMS
azure-keyvault==4.2.0  # For Azure
google-cloud-kms==2.19.2  # For GCP
```

## 🔒 Environment Variables

```env
# MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB_NAME=pran-protocol

# Encryption
MASTER_ENCRYPTION_KEY=<64-character-hex-string>
ENCRYPTION_KEY_ROTATION_DAYS=90

# Blockchain (Polygon Mumbai Testnet for testing)
BLOCKCHAIN_PROVIDER_URL=https://polygon-mumbai.g.alchemy.com/v2/YOUR-API-KEY
CONTRACT_ADDRESS=0x...
BLOCKCHAIN_PRIVATE_KEY=0x...

# AWS KMS (if using)
AWS_KMS_KEY_ID=arn:aws:kms:...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## 📈 Benefits of This Architecture

### Security
✅ End-to-end encryption
✅ Immutable audit trail
✅ Tamper-proof records
✅ HIPAA compliant

### Scalability
✅ Cloud-based (auto-scaling)
✅ Global availability
✅ No local storage limits

### Compliance
✅ Audit logs for every action
✅ Data integrity verification
✅ Access control with MFA
✅ Consent management

### Reliability
✅ MongoDB Atlas 99.99% uptime
✅ Blockchain redundancy
✅ Automated backups
✅ Disaster recovery

## 🚀 Next Steps

1. Review this architecture with your team
2. Choose blockchain option (I recommend Polygon for MVP)
3. Create MongoDB Atlas account
4. Set up development environment
5. Start with Phase 1 implementation

Would you like me to proceed with implementing any of these components?
