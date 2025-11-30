import hashlib
import json
import os
from datetime import datetime
from typing import List, Dict, Any

LEDGER_FILE = "audit_ledger.json"

class Block:
    def __init__(self, index: int, timestamp: str, data: Dict[str, Any], previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.load_chain()

    def create_genesis_block(self):
        genesis_block = Block(0, str(datetime.utcnow()), {"message": "Genesis Block"}, "0")
        self.chain.append(genesis_block)
        self.save_chain()

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, user_id: int, action: str, details: str):
        latest_block = self.get_latest_block()
        new_data = {
            "user_id": user_id,
            "action": action,
            "details": details
        }
        new_block = Block(
            index=latest_block.index + 1,
            timestamp=str(datetime.utcnow()),
            data=new_data,
            previous_hash=latest_block.hash
        )
        self.chain.append(new_block)
        self.save_chain()
        return new_block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False
        return True

    def save_chain(self):
        chain_data = [block.__dict__ for block in self.chain]
        with open(LEDGER_FILE, "w") as f:
            json.dump(chain_data, f, indent=4)

    def load_chain(self):
        if os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, "r") as f:
                try:
                    chain_data = json.load(f)
                    self.chain = []
                    for block_data in chain_data:
                        block = Block(
                            block_data["index"],
                            block_data["timestamp"],
                            block_data["data"],
                            block_data["previous_hash"]
                        )
                        block.hash = block_data["hash"] # Restore hash
                        self.chain.append(block)
                except json.JSONDecodeError:
                    self.create_genesis_block()
        else:
            self.create_genesis_block()

# Global instance
audit_ledger = Blockchain()
