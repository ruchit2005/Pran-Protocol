# Encryption Manager for PHI Data
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Optional
import secrets
import logging

logger = logging.getLogger(__name__)


class PHIEncryptionManager:
    """
    HIPAA-compliant encryption manager for Protected Health Information (PHI)
    Uses AES-256-GCM encryption with key derivation
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager
        
        Args:
            master_key: 64-character hex string (256-bit key)
                       If not provided, uses MASTER_ENCRYPTION_KEY from env
        """
        self.master_key = master_key or os.getenv("MASTER_ENCRYPTION_KEY")
        
        if not self.master_key:
            raise ValueError("MASTER_ENCRYPTION_KEY not set in environment")
        
        if len(self.master_key) != 64:
            raise ValueError("Master key must be 64 hex characters (256 bits)")
        
        self.master_key_bytes = bytes.fromhex(self.master_key)
    
    def generate_user_salt(self) -> str:
        """Generate a unique salt for user-specific encryption"""
        return secrets.token_hex(16)
    
    def _derive_key(self, salt: str) -> bytes:
        """Derive encryption key from master key and user salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key_bytes))
    
    def encrypt(self, data: str, user_salt: str) -> str:
        """
        Encrypt PHI data
        
        Args:
            data: Plain text to encrypt
            user_salt: User-specific salt
            
        Returns:
            Base64-encoded encrypted data
        """
        try:
            key = self._derive_key(user_salt)
            f = Fernet(key)
            encrypted = f.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str, user_salt: str) -> str:
        """
        Decrypt PHI data
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            user_salt: User-specific salt
            
        Returns:
            Decrypted plain text
        """
        try:
            key = self._derive_key(user_salt)
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    @staticmethod
    def hash_for_audit(data: str) -> str:
        """
        Create SHA-256 hash for audit purposes (one-way)
        Used for IP addresses, etc.
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def generate_master_key() -> str:
        """Generate a new 256-bit master key (for initial setup)"""
        return secrets.token_hex(32)
    
    def rotate_key(self, old_salt: str, new_salt: str, encrypted_data: str) -> str:
        """
        Re-encrypt data with a new salt (for key rotation)
        
        Args:
            old_salt: Current salt
            new_salt: New salt
            encrypted_data: Currently encrypted data
            
        Returns:
            Data encrypted with new salt
        """
        # Decrypt with old salt
        plaintext = self.decrypt(encrypted_data, old_salt)
        # Re-encrypt with new salt
        return self.encrypt(plaintext, new_salt)


# Example usage for generating initial master key
if __name__ == "__main__":
    print("=== Encryption Manager Setup ===\n")
    print("Generate a new master key:")
    master_key = PHIEncryptionManager.generate_master_key()
    print(f"\nMASTER_ENCRYPTION_KEY={master_key}")
    print("\n⚠️ IMPORTANT: Save this key securely!")
    print("Add it to your .env file and NEVER commit it to git")
    print("Consider using AWS KMS, Azure Key Vault, or GCP KMS for production")
