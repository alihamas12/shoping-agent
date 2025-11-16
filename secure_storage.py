from cryptography.fernet import Fernet
import base64
import os

class SecureStorage:
    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key()
            print(f"Set ENCRYPTION_KEY in .env: {key.decode()}")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    def encrypt(self, data):
        """Encrypt personal data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data):
        """Decrypt personal data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

secure_storage = SecureStorage()