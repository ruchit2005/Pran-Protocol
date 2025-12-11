# Smart Contract Deployment Script
import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from dotenv import load_dotenv

load_dotenv()

# Install Solidity compiler
print("📦 Installing Solidity compiler...")
install_solc("0.8.20")

# Read contract source
with open("contracts/HealthcareAudit.sol", "r") as file:
    contract_source = file.read()

# Compile contract
print("🔨 Compiling smart contract...")
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"HealthcareAudit.sol": {"content": contract_source}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            }
        },
    },
    solc_version="0.8.20",
)

# Extract bytecode and ABI
bytecode = compiled_sol["contracts"]["HealthcareAudit.sol"]["HealthcareAudit"]["evm"]["bytecode"]["object"]
abi = compiled_sol["contracts"]["HealthcareAudit.sol"]["HealthcareAudit"]["abi"]

# Save ABI to file
with open("contracts/HealthcareAudit.json", "w") as file:
    json.dump({"abi": abi, "bytecode": bytecode}, file, indent=2)
print("✅ Contract compiled and ABI saved")

# Connect to blockchain
provider_url = os.getenv("BLOCKCHAIN_PROVIDER_URL")
private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")

if not provider_url or not private_key:
    print("❌ BLOCKCHAIN_PROVIDER_URL and BLOCKCHAIN_PRIVATE_KEY must be set in .env")
    exit(1)

print(f"\n🌐 Connecting to blockchain: {provider_url}")
w3 = Web3(Web3.HTTPProvider(provider_url))

if not w3.is_connected():
    print("❌ Failed to connect to blockchain")
    exit(1)

print(f"✅ Connected! Chain ID: {w3.eth.chain_id}")

# Get account
account = w3.eth.account.from_key(private_key)
print(f"📍 Deploying from: {account.address}")

# Check balance
balance = w3.eth.get_balance(account.address)
balance_eth = w3.from_wei(balance, 'ether')
print(f"💰 Balance: {balance_eth} ETH/MATIC")

if balance == 0:
    print("❌ No balance! Get testnet tokens from a faucet:")
    print("   Mumbai: https://faucet.polygon.technology/")
    exit(1)

# Create contract instance
HealthcareAudit = w3.eth.contract(abi=abi, bytecode=bytecode)

# Build transaction
print("\n📝 Building deployment transaction...")
transaction = HealthcareAudit.constructor().build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 3000000,
    "gasPrice": w3.eth.gas_price,
})

# Sign transaction
print("🔏 Signing transaction...")
signed_txn = w3.eth.account.sign_transaction(transaction, private_key)

# Send transaction
print("📤 Sending transaction...")
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
print(f"   Transaction hash: {tx_hash.hex()}")

# Wait for receipt
print("⏳ Waiting for confirmation...")
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

if tx_receipt.status == 1:
    print(f"\n✅ Contract deployed successfully!")
    print(f"   Contract address: {tx_receipt.contractAddress}")
    print(f"   Block number: {tx_receipt.blockNumber}")
    print(f"   Gas used: {tx_receipt.gasUsed}")
    
    print("\n📋 Add this to your .env file:")
    print(f"CONTRACT_ADDRESS={tx_receipt.contractAddress}")
    
    # Save to file
    with open(".contract_address", "w") as f:
        f.write(tx_receipt.contractAddress)
    
else:
    print("❌ Deployment failed!")
    print(tx_receipt)
