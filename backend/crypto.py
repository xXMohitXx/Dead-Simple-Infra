import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Master key for encryption - in production, this should be from env or KMS
MASTER_KEY = os.environ.get('MASTER_ENCRYPTION_KEY', 'dev-master-key-32-bytes-long!!').encode()

# Derive a proper 256-bit key
def get_encryption_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'dead-simple-infra-salt',  # In production, use random salt per secret
        iterations=100000,
    )
    return kdf.derive(MASTER_KEY)

def encrypt_secret(plaintext: str) -> str:
    """
    Encrypt a secret using AES-256-GCM.
    Returns base64-encoded nonce + ciphertext.
    """
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    
    # Combine nonce + ciphertext and encode as base64
    encrypted_data = nonce + ciphertext
    return base64.b64encode(encrypted_data).decode('utf-8')

def decrypt_secret(encrypted_data: str) -> str:
    """
    Decrypt a secret using AES-256-GCM.
    """
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    
    # Decode from base64
    encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
    
    # Extract nonce and ciphertext
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    
    # Decrypt
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')
