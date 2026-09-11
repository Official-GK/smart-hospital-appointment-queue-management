import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
from dotenv import load_dotenv

load_dotenv()

# We expect ENCRYPTION_KEY to be a 64-character hex string (32 bytes = 256 bits)
hex_key = os.getenv("ENCRYPTION_KEY")
if not hex_key:
    # Fallback for development if not provided, though it will break on restart if not persisted
    hex_key = secrets.token_hex(32)
    os.environ["ENCRYPTION_KEY"] = hex_key

# AESGCM needs a bytes key
try:
    key = bytes.fromhex(hex_key)
except ValueError:
    key = b'0' * 32  # Fallback dummy key to prevent crash if badly formatted

def encrypt_string(plaintext: str) -> str:
    """
    Encrypts a string using AES-256 GCM.
    Returns a base64 encoded string containing the nonce and ciphertext.
    Format: base64(nonce + ciphertext)
    """
    if not plaintext:
        return plaintext
        
    aesgcm = AESGCM(key)
    # Generate a random 12-byte nonce (standard for GCM)
    nonce = secrets.token_bytes(12)
    
    # Encrypt
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    
    # Combine nonce and ciphertext and encode as base64
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode('utf-8')

def decrypt_string(encrypted_b64: str) -> str:
    """
    Decrypts a base64 encoded string containing the nonce and ciphertext using AES-256 GCM.
    If decryption fails or format is invalid, returns the original string (to handle unencrypted legacy data gracefully).
    """
    if not encrypted_b64:
        return encrypted_b64
        
    try:
        combined = base64.b64decode(encrypted_b64.encode('utf-8'))
        if len(combined) < 12:
            return encrypted_b64 # Not a valid encrypted payload
            
        nonce = combined[:12]
        ciphertext = combined[12:]
        
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode('utf-8')
    except Exception:
        # If it fails to decode or decrypt, it might just be legacy plain text
        return encrypted_b64
