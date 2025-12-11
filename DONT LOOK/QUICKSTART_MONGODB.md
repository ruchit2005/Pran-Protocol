# Quick Start: MongoDB + Blockchain Setup

## 🚀 Step-by-Step Setup Guide

### Step 1: Install Dependencies (5 minutes)

```bash
pip install -r requirements.txt
```

### Step 2: Generate Encryption Key (1 minute)

```bash
python -m src.security.encryption
```

**Output:**
```
=== Encryption Manager Setup ===

Generate a new master key:

MASTER_ENCRYPTION_KEY=a1b2c3d4e5f6...  (64 characters)

⚠️ IMPORTANT: Save this key securely!
```

**Add to `.env` file:**
```env
MASTER_ENCRYPTION_KEY=<your-generated-key>
```

### Step 3: Setup MongoDB Atlas (10 minutes)

1. **Create Account**: Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)

2. **Create Cluster**:
   - Click "Build a Database"
   - Choose "M0 Free" tier
   - Select closest region
   - Click "Create"

3. **Create Database User**:
   - Go to "Database Access"
   - Add new user: `pran-protocol-app`
   - Set strong password
   - Role: "Atlas admin" (or readWrite on specific database)

4. **Configure Network Access**:
   - Go to "Network Access"
   - Add IP: `0.0.0.0/0` (for development only!)
   - For production: Add your server IPs only

5. **Get Connection String**:
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy connection string
   - Replace `<password>` with your actual password

**Add to `.env` file:**
```env
MONGODB_URI=mongodb+srv://pran-protocol-app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=pran-protocol
```

### Step 4: Setup Blockchain (15 minutes)

#### Option A: Polygon Mumbai (Testnet - FREE)

1. **Create Alchemy Account**: [Alchemy](https://www.alchemy.com/)
   - Create new app
   - Choose "Polygon Mumbai"
   - Copy API key

2. **Get Testnet Wallet**:
   ```bash
   # Install MetaMask browser extension
   # Create new wallet
   # Switch to Mumbai testnet
   # Copy private key (Settings > Security & Privacy > Reveal Private Key)
   ```

3. **Get Free Test MATIC**:
   - Visit [Mumbai Faucet](https://faucet.polygon.technology/)
   - Paste your wallet address
   - Receive free test MATIC

4. **Deploy Smart Contract** (we'll provide deployed address):
   ```
   Contract: 0x... (will be provided)
   ```

**Add to `.env` file:**
```env
BLOCKCHAIN_PROVIDER_URL=https://polygon-mumbai.g.alchemy.com/v2/YOUR-API-KEY
CONTRACT_ADDRESS=0x... (deployed contract address)
BLOCKCHAIN_PRIVATE_KEY=0x... (your wallet private key)
```

#### Option B: Skip Blockchain (Testing)

If you want to test without blockchain:
```env
# Leave these empty - blockchain will be disabled
BLOCKCHAIN_PROVIDER_URL=
CONTRACT_ADDRESS=
BLOCKCHAIN_PRIVATE_KEY=
```

### Step 5: Migrate Data (5 minutes)

```bash
# Make sure your .env has MongoDB and encryption keys set
python migrate_to_mongodb.py
```

**Expected output:**
```
=== Starting SQLite to MongoDB Migration ===

✅ Connected to MongoDB: pran-protocol
📦 Migrating users...
   ✓ Migrated user: user@example.com -> 65a1b2c3d4e5f6789
✅ Users migrated: 5

📦 Migrating sessions...
   ✓ Migrated session: Chat about headache...
✅ Sessions migrated: 12

📦 Migrating messages...
✅ Messages migrated: 45

=== Migration Complete ===
```

### Step 6: Update API Code (Optional - for later)

The migration script creates encrypted data in MongoDB.
To use MongoDB in your API, you'll need to update `api.py` to use the new database.

**We can do this in the next phase!**

## ✅ Verification

### Test Encryption:
```bash
python -c "from src.security.encryption import PHIEncryptionManager; \
em = PHIEncryptionManager(); \
salt = em.generate_user_salt(); \
encrypted = em.encrypt('test data', salt); \
print(f'Encrypted: {encrypted[:50]}...'); \
decrypted = em.decrypt(encrypted, salt); \
print(f'Decrypted: {decrypted}')"
```

**Expected:**
```
Encrypted: gAAAAABl...
Decrypted: test data
```

### Test MongoDB Connection:
```bash
python -c "import asyncio; \
from src.database.mongodb_manager import mongodb_manager; \
async def test(): \
    await mongodb_manager.connect(); \
    print('✅ MongoDB connected'); \
    await mongodb_manager.close(); \
asyncio.run(test())"
```

**Expected:**
```
✅ Connected to MongoDB: pran-protocol
✅ Database indexes created
✅ MongoDB connected
```

### Test Blockchain (if enabled):
```bash
python -c "from src.blockchain.audit_logger import blockchain_logger; \
print(f'Blockchain enabled: {blockchain_logger.enabled}'); \
if blockchain_logger.enabled: \
    print(f'Chain ID: {blockchain_logger.w3.eth.chain_id}'); \
    print(f'Account: {blockchain_logger.account.address}')"
```

**Expected (if enabled):**
```
✅ Blockchain audit logger connected: 80001
   Account: 0x...
Blockchain enabled: True
Chain ID: 80001
Account: 0x...
```

## 🔒 Security Checklist

- [ ] `MASTER_ENCRYPTION_KEY` is 64 characters (256-bit)
- [ ] MongoDB has encryption at rest enabled
- [ ] Network access is restricted (not 0.0.0.0/0 in production)
- [ ] Strong database user password
- [ ] `.env` file is in `.gitignore`
- [ ] Blockchain private key is never logged or committed
- [ ] Test data decryption works
- [ ] Audit logs are being created

## 📊 What You Get

### Before (SQLite):
- ❌ Local file (can be lost)
- ❌ No encryption
- ❌ No audit trail
- ❌ Not HIPAA compliant

### After (MongoDB + Blockchain):
- ✅ Cloud-based (redundant, backed up)
- ✅ End-to-end encrypted PHI
- ✅ Immutable blockchain audit trail
- ✅ HIPAA-compliant architecture
- ✅ Scalable to millions of users
- ✅ Tamper-proof records

## 💰 Cost Estimate

- **MongoDB Atlas M0**: $0/month (512MB storage, 100 connections)
- **Polygon Mumbai**: $0 (testnet)
- **Polygon Mainnet**: ~$0.01-0.05 per transaction
- **Total for testing**: **$0/month**

## 🚨 Troubleshooting

### "MASTER_ENCRYPTION_KEY not set"
```bash
# Generate new key:
python -m src.security.encryption

# Add to .env file
```

### "Failed to connect to MongoDB"
- Check `MONGODB_URI` in `.env`
- Verify network access (0.0.0.0/0 for testing)
- Check database user credentials

### "Blockchain not configured"
- This is OK for testing! Blockchain is optional
- To enable: Follow Step 4 above

### "Migration failed"
- Ensure `healthcare.db` exists
- Check MongoDB connection
- Verify encryption key is set

## 🎯 Next Steps

1. ✅ Complete setup above
2. ✅ Run migration script
3. ✅ Verify all tests pass
4. 📝 Update API to use MongoDB (next phase)
5. 🌐 Deploy smart contract (if using blockchain)
6. 🧪 Test end-to-end flow

## 📞 Need Help?

Check the detailed guide: `MONGODB_BLOCKCHAIN_SETUP.md`
