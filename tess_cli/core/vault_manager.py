
import os
import json
import base64
from cryptography.fernet import Fernet
from .logger import setup_logger

logger = setup_logger("VaultManager")

class VaultManager:
    """
    🛡️ Secure Storage for User Secrets
    Uses Fernet (symmetric encryption) to store sensitive data (API keys, passwords, notes).
    """
    
    VAULT_DIR = os.path.join(os.path.expanduser("~"), ".tess")
    VAULT_FILE = os.path.join(VAULT_DIR, "vault.json.enc")
    KEY_FILE = os.path.join(VAULT_DIR, ".key")

    def __init__(self):
        self._ensure_setup()
        self.cipher = Fernet(self._load_key())
        self.secrets = self._load_vault()

    def _ensure_setup(self):
        """Ensure vault directory and key exist."""
        os.makedirs(self.VAULT_DIR, exist_ok=True)
        if not os.path.exists(self.KEY_FILE):
            key = Fernet.generate_key()
            with open(self.KEY_FILE, "wb") as f:
                f.write(key)
            self._lock_key_file()

    def _lock_key_file(self):
        """
        Restrict the key file to the current user only using Windows icacls.
        Equivalent to chmod 600 on Unix.
        Falls back silently if icacls is unavailable.
        """
        import subprocess
        try:
            username = os.environ.get("USERNAME", "")
            if not username:
                return
            # Remove all inherited ACEs, then grant only the current user full control
            subprocess.run(
                ["icacls", self.KEY_FILE, "/inheritance:r", "/grant:r", f"{username}:F"],
                check=False,
                capture_output=True,
                timeout=5
            )
            logger.info("Vault key file permissions locked to current user.")
        except Exception as e:
            logger.warning(f"Could not lock vault key permissions: {e}")
            
    def _load_key(self):
        """Load the encryption key."""
        with open(self.KEY_FILE, "rb") as f:
            return f.read()

    def _load_vault(self):
        """Load and decrypt the vault."""
        if not os.path.exists(self.VAULT_FILE):
            return {}
        
        try:
            with open(self.VAULT_FILE, "rb") as f:
                encrypted_data = f.read()
                if not encrypted_data: return {}
                
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to unlock vault: {e}")
            return {}

    def _save_vault(self):
        """Encrypt and save the vault."""
        try:
            json_data = json.dumps(self.secrets).encode()
            encrypted_data = self.cipher.encrypt(json_data)
            
            with open(self.VAULT_FILE, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")

    # ─── Public API ──────────────────────────────────────────────────────

    def store_secret(self, key, value):
        """Securely store a secret."""
        self.secrets[key] = value
        self._save_vault()
        return f"Secret '{key}' stored securely."

    def get_secret(self, key):
        """Retrieve a secret."""
        return self.secrets.get(key, None)

    def list_secrets(self):
        """List available secret keys (names only)."""
        return list(self.secrets.keys())

    def delete_secret(self, key):
        """Remove a secret."""
        if key in self.secrets:
            del self.secrets[key]
            self._save_vault()
            return f"Secret '{key}' deleted."
        return f"Secret '{key}' not found."
