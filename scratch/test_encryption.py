import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.helpers import encrypt_string, decrypt_string

def test_encryption_decryption():
    test_str = "MySuperSecretSteamPassword123!"
    encrypted = encrypt_string(test_str)
    print(f"Encrypted string: {encrypted}")
    
    decrypted = decrypt_string(encrypted)
    print(f"Decrypted string: {decrypted}")
    
    assert decrypted == test_str, f"Decryption failed! Expected '{test_str}', got '{decrypted}'"
    print("Encryption & Decryption test passed successfully!")

if __name__ == "__main__":
    test_encryption_decryption()
