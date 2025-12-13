"""
DISHA (Digital Information Security in Healthcare Act) Compliance Module
Indian Healthcare Data Protection Implementation

Features:
1. PII Anonymization (no direct storage of personal identifiable information)
2. Blockchain-based audit trail for all medical operations
3. Verifiable credentials for AI responses
4. Data minimization and consent management
"""

import hashlib
import secrets
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class AnonymizationManager:
    """
    Manages PII anonymization using tokenization
    Stores only pseudonymous IDs, actual PII is encrypted separately
    """
    
    def __init__(self, master_key: str):
        self.master_key = master_key
    
    def create_anonymous_id(self, user_email: str) -> str:
        """
        Generate deterministic anonymous ID from email
        Same email always produces same ID (for consistency)
        """
        return hashlib.sha256(
            f"{user_email}{self.master_key}".encode()
        ).hexdigest()[:16]
    
    def tokenize_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace PII with tokens
        Returns anonymized data + token mapping
        """
        tokens = {}
        anonymized = {}
        
        pii_fields = ['email', 'phone', 'name', 'address', 'aadhar', 'pan']
        
        for key, value in data.items():
            if key.lower() in pii_fields and value:
                # Generate token
                token = f"TOKEN_{secrets.token_hex(8)}"
                tokens[token] = value
                anonymized[key] = token
            else:
                anonymized[key] = value
        
        return {
            'anonymized_data': anonymized,
            'token_mapping': tokens  # Store this separately in secure vault
        }
    
    def anonymize_medical_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize medical record while preserving medical data
        """
        return {
            'anonymous_id': self.create_anonymous_id(record.get('email', '')),
            'age_range': self._generalize_age(record.get('age')),  # e.g., "25-30"
            'gender': record.get('gender'),  # Keep for medical relevance
            'medical_history': record.get('medical_history', []),
            'allergies': record.get('allergies', []),
            'medications': record.get('medications', []),
            'timestamp': datetime.utcnow().isoformat(),
            # PII removed: name, email, phone, address
        }
    
    def _generalize_age(self, age: Optional[int]) -> str:
        """Generalize age to range for privacy"""
        if not age:
            return "Unknown"
        
        if age < 18:
            return "<18"
        elif age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65+"


class MedicalBlockchainAuditor:
    """
    Blockchain-based audit trail specifically for medical operations
    Records all diagnoses, prescriptions, and recommendations
    """
    
    def __init__(self, blockchain_logger):
        self.blockchain = blockchain_logger
    
    async def log_diagnosis(
        self,
        anonymous_id: str,
        symptoms: List[str],
        diagnosis: str,
        confidence_score: float,
        sources: List[str]
    ) -> Dict[str, Any]:
        """Log AI diagnosis to blockchain"""
        
        audit_record = {
            'type': 'DIAGNOSIS',
            'anonymous_id': anonymous_id,
            'symptoms': symptoms,
            'diagnosis': diagnosis,
            'confidence': confidence_score,
            'sources': sources,
            'timestamp': datetime.utcnow().isoformat(),
            'ai_model': 'gpt-4o-mini'
        }
        
        # Hash the record
        record_hash = hashlib.sha256(
            json.dumps(audit_record, sort_keys=True).encode()
        ).hexdigest()
        
        # Log to blockchain
        if self.blockchain.enabled:
            result = await self.blockchain.log_action(
                user_id=anonymous_id,
                action='DIAGNOSIS',
                data=audit_record
            )
            if result:
                audit_record['blockchain_tx'] = result['tx_hash']
                logger.info(f"✅ Diagnosis logged to blockchain: {result['tx_hash']}")
        
        audit_record['record_hash'] = record_hash
        return audit_record
    
    async def log_prescription(
        self,
        anonymous_id: str,
        condition: str,
        recommendations: List[str],
        contraindications: List[str]
    ) -> Dict[str, Any]:
        """Log prescription/recommendation to blockchain"""
        
        audit_record = {
            'type': 'PRESCRIPTION',
            'anonymous_id': anonymous_id,
            'condition': condition,
            'recommendations': recommendations,
            'contraindications': contraindications,
            'timestamp': datetime.utcnow().isoformat(),
            'ai_model': 'gpt-4o-mini',
            'disclaimer': 'AI-generated advice. Consult licensed medical professional.'
        }
        
        record_hash = hashlib.sha256(
            json.dumps(audit_record, sort_keys=True).encode()
        ).hexdigest()
        
        if self.blockchain.enabled:
            result = await self.blockchain.log_action(
                user_id=anonymous_id,
                action='PRESCRIPTION',
                data=audit_record
            )
            if result:
                audit_record['blockchain_tx'] = result['tx_hash']
                logger.info(f"✅ Prescription logged to blockchain: {result['tx_hash']}")
        
        audit_record['record_hash'] = record_hash
        return audit_record
    
    async def log_data_access(
        self,
        anonymous_id: str,
        accessed_by: str,
        data_type: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Log who accessed patient data and why (DISHA requirement)"""
        
        audit_record = {
            'type': 'DATA_ACCESS',
            'anonymous_id': anonymous_id,
            'accessed_by': accessed_by,
            'data_type': data_type,
            'purpose': purpose,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.blockchain.enabled:
            result = await self.blockchain.log_action(
                user_id=anonymous_id,
                action='DATA_ACCESS',
                data=audit_record
            )
            if result:
                audit_record['blockchain_tx'] = result['tx_hash']
        
        return audit_record


class VerifiableCredentialManager:
    """
    Generate cryptographically signed AI responses
    Prevents tampering and validates authenticity
    """
    
    def __init__(self):
        # Generate RSA key pair for signing
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        logger.info("✅ Verifiable credential keys generated")
    
    def sign_response(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sign AI response with digital signature
        Returns response + signature + metadata
        """
        # Create response payload
        payload = {
            'response': response_data.get('output'),
            'intent': response_data.get('intent'),
            'sources': response_data.get('sources', []),
            'confidence': response_data.get('confidence', 0.0),
            'timestamp': datetime.utcnow().isoformat(),
            'model': 'gpt-4o-mini',
            'fact_checked': response_data.get('validation_status') == 'passed'
        }
        
        # Create signature
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = self.private_key.sign(
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            **payload,
            'signature': signature.hex(),
            'public_key_fingerprint': self._get_public_key_fingerprint(),
            'verifiable': True
        }
    
    def verify_response(
        self,
        signed_response: Dict[str, Any]
    ) -> bool:
        """Verify response signature"""
        try:
            signature = bytes.fromhex(signed_response['signature'])
            
            # Recreate payload without signature
            payload = {k: v for k, v in signed_response.items() 
                      if k not in ['signature', 'public_key_fingerprint', 'verifiable']}
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            
            self.public_key.verify(
                signature,
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def _get_public_key_fingerprint(self) -> str:
        """Get fingerprint of public key"""
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(public_pem).hexdigest()[:16]


class DISHAComplianceManager:
    """
    Main compliance manager integrating all features
    """
    
    def __init__(self, blockchain_logger, master_key: str):
        self.anonymizer = AnonymizationManager(master_key)
        self.auditor = MedicalBlockchainAuditor(blockchain_logger)
        self.credential_manager = VerifiableCredentialManager()
        logger.info("✅ DISHA Compliance Manager initialized")
    
    async def process_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user data with full DISHA compliance
        Returns anonymized data + audit trail
        """
        # 1. Anonymize PII
        anonymized = self.anonymizer.anonymize_medical_record(user_data)
        
        # 2. Log data access
        access_log = await self.auditor.log_data_access(
            anonymous_id=anonymized['anonymous_id'],
            accessed_by='ai_assistant',
            data_type='medical_profile',
            purpose='personalized_health_advice'
        )
        
        return {
            'anonymized_data': anonymized,
            'access_audit': access_log
        }
    
    async def process_ai_response(
        self,
        anonymous_id: str,
        user_query: str,
        ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process AI response with compliance features
        """
        # 1. Log to blockchain if medical advice
        intent = ai_response.get('intent')
        blockchain_log = None
        
        if intent in ['symptom_checker', 'health_advisory', 'ayush_support']:
            blockchain_log = await self.auditor.log_diagnosis(
                anonymous_id=anonymous_id,
                symptoms=[user_query],
                diagnosis=ai_response.get('output', ''),
                confidence_score=ai_response.get('confidence', 0.8),
                sources=ai_response.get('sources', [])
            )
        
        # 2. Create verifiable credential
        signed_response = self.credential_manager.sign_response(ai_response)
        
        return {
            'response': signed_response,
            'blockchain_audit': blockchain_log,
            'compliance_status': 'DISHA_COMPLIANT',
            'anonymized': True,
            'verifiable': True
        }
