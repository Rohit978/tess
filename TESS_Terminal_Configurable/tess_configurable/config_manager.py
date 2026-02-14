"""
Configuration Manager for TESS Configurable Edition.
Handles loading, saving, and validation of user settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    # api_keys format: {"provider": ["key1", "key2", ...]} for multiple keys per provider
    api_keys: Dict[str, List[str]] = field(default_factory=dict)
    temperature: float = 0.1
    max_tokens: int = 2048
    backup_providers: List[str] = field(default_factory=lambda: ["deepseek", "gemini"])


@dataclass
class SecurityConfig:
    """Security settings."""
    level: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    safe_mode: bool = True
    confirm_dangerous: bool = True
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf", "del /s", "format", "rd /s", "shutdown"
    ])
    sensitive_paths: List[str] = field(default_factory=lambda: [
        "C:\\Windows", "System32", "\\.ssh\\", "\\.aws\\"
    ])


@dataclass
class FeatureConfig:
    """Feature toggles."""
    # Communication
    whatsapp: bool = False
    gmail: bool = False
    calendar: bool = False
    telegram_bot: bool = False
    
    # Media & Web
    youtube: bool = False
    web_search: bool = True
    web_scraping: bool = False
    
    # AI Capabilities
    planner: bool = True
    skills: bool = True
    research: bool = True
    code_generation: bool = True
    trip_planner: bool = True
    file_converter: bool = True
    
    # Memory & Learning
    memory: bool = True
    librarian: bool = False  # File watcher - resource intensive
    command_indexer: bool = False
    
    # Task Management
    scheduler: bool = True
    task_registry: bool = True
    organizer: bool = True
    
    # Multi-user
    multi_user: bool = False
    
    # Web Interface
    web_interface: bool = False
    web_port: int = 8000


@dataclass
class PathConfig:
    """Directory paths."""
    memory_dir: str = ""
    logs_dir: str = ""
    skills_dir: str = ""
    temp_dir: str = ""
    vector_db: str = ""
    data_dir: str = ""


@dataclass
class WhatsAppConfig:
    """WhatsApp configuration."""
    enabled: bool = False
    # QR code scanning happens on first run


@dataclass
class GoogleConfig:
    """Google services configuration."""
    credentials_file: str = ""
    token_file: str = ""


@dataclass
class TelegramConfig:
    """Telegram configuration."""
    bot_token: str = ""
    user_id: str = ""
    allowed_users: List[str] = field(default_factory=list)


@dataclass
class TessConfig:
    """Main configuration container."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    first_run: bool = True
    version: str = "1.1.0"


class ConfigManager:
    """
    Manages TESS configuration with persistent storage.
    """
    
    def __init__(self):
        self.config_dir = Path.home() / ".tess"
        self.config_file = self.config_dir / "config.json"
        self.config = TessConfig()
        self._ensure_directories()
        self._init_default_paths()
        
    def _ensure_directories(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def _init_default_paths(self):
        """Initialize default paths."""
        self.config.paths.memory_dir = str(self.config_dir / "memory")
        self.config.paths.logs_dir = str(self.config_dir / "logs")
        self.config.paths.skills_dir = str(self.config_dir / "skills")
        self.config.paths.temp_dir = str(self.config_dir / "temp")
        self.config.paths.vector_db = str(self.config_dir / "vector_db")
        self.config.paths.data_dir = str(self.config_dir / "data")
        
        # Create subdirectories
        for path in [self.config.paths.memory_dir, 
                     self.config.paths.logs_dir,
                     self.config.paths.skills_dir,
                     self.config.paths.temp_dir,
                     self.config.paths.vector_db,
                     self.config.paths.data_dir]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def load(self) -> bool:
        """
        Load configuration from file.
        Returns True if successful, False if file doesn't exist.
        """
        if not self.config_file.exists():
            return False
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Parse nested structures
            telegram_data = data.get('telegram', {})
            # Backward compatibility: flatten if needed or read older keys
            if not telegram_data:
                telegram_data = {
                    'bot_token': data.get('telegram_token', ''),
                    'user_id': data.get('telegram_user_id', ''),
                    'allowed_users': data.get('telegram_allowed_users', [])
                }
            
            self.config = TessConfig(
                llm=LLMConfig(**data.get('llm', {})),
                security=SecurityConfig(**data.get('security', {})),
                features=FeatureConfig(**data.get('features', {})),
                paths=PathConfig(**data.get('paths', {})),
                whatsapp=WhatsAppConfig(**data.get('whatsapp', {})),
                google=GoogleConfig(**data.get('google', {})),
                telegram=TelegramConfig(**telegram_data),
                first_run=data.get('first_run', False),
                version=data.get('version', '1.0.0')
            )
            return True
        except Exception as e:
            print(f"⚠️  Error loading config: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save configuration to file.
        Returns True if successful.
        """
        try:
            # Convert dataclass to dict
            data = {
                'llm': asdict(self.config.llm),
                'security': asdict(self.config.security),
                'features': asdict(self.config.features),
                'paths': asdict(self.config.paths),
                'whatsapp': asdict(self.config.whatsapp),
                'google': asdict(self.config.google),
                'telegram': asdict(self.config.telegram),
                'first_run': self.config.first_run,
                'version': self.config.version
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Secure the config file (Windows)
            try:
                os.chmod(self.config_file, 0o600)
            except Exception:
                pass  # Windows may not support this
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def get_api_key(self, provider: str, index: int = 0) -> Optional[str]:
        """
        Get API key for a specific provider.
        Returns the key at the specified index (default: first key).
        Supports backward compatibility with old single-key format.
        """
        provider = provider.lower()
        keys = self.config.llm.api_keys.get(provider)
        
        if not keys:
            return None
        
        # Handle backward compatibility: convert single string to list
        if isinstance(keys, str):
            self.config.llm.api_keys[provider] = [keys]
            return keys
        
        # Handle list format
        if isinstance(keys, list) and 0 <= index < len(keys):
            return keys[index]
        
        return None
    
    def get_all_api_keys(self, provider: str) -> List[str]:
        """Get all API keys for a specific provider."""
        provider = provider.lower()
        keys = self.config.llm.api_keys.get(provider, [])
        
        # Handle backward compatibility: convert single string to list
        if isinstance(keys, str):
            return [keys]
        
        return keys if isinstance(keys, list) else []
    
    def set_api_key(self, provider: str, key: str):
        """
        Set API key for a specific provider (replaces all keys).
        Use add_api_key() to add additional keys.
        """
        self.config.llm.api_keys[provider.lower()] = [key]
    
    def add_api_key(self, provider: str, key: str) -> bool:
        """
        Add an additional API key for a specific provider.
        Returns True if added successfully.
        """
        provider = provider.lower()
        existing = self.config.llm.api_keys.get(provider, [])
        
        # Handle backward compatibility
        if isinstance(existing, str):
            existing = [existing]
        elif not isinstance(existing, list):
            existing = []
        
        # Don't add duplicates
        if key not in existing:
            self.config.llm.api_keys[provider] = existing + [key]
            return True
        return False
    
    def remove_api_key(self, provider: str, index: int) -> bool:
        """
        Remove an API key at the specified index for a provider.
        Returns True if removed successfully.
        """
        provider = provider.lower()
        keys = self.config.llm.api_keys.get(provider, [])
        
        if isinstance(keys, str):
            if index == 0:
                self.config.llm.api_keys[provider] = []
                return True
            return False
        
        if isinstance(keys, list) and 0 <= index < len(keys):
            keys.pop(index)
            self.config.llm.api_keys[provider] = keys
            return True
        return False
    
    def validate_api_key(self, provider: str, key: str) -> tuple[bool, str]:
        """
        Validate an API key by making a test request.
        Returns (is_valid, message).
        """
        provider = provider.lower()
        
        if not key or len(key) < 10:
            return False, "Key is too short or empty"
        
        # Basic format validation
        if provider == "groq" and not key.startswith("gsk_"):
            return False, "Groq keys should start with 'gsk_'"
        if provider == "openai" and not key.startswith("sk-"):
            return False, "OpenAI keys should start with 'sk-'"
            
        return True, "Format looks valid"
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = TessConfig()
        self._init_default_paths()
        
    def export_config(self, path: str) -> bool:
        """Export configuration to a specific path."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    def import_config(self, path: str) -> bool:
        """Import configuration from a specific path."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate required fields
            if 'llm' not in data or 'security' not in data:
                return False
                
            self.config = TessConfig(
                llm=LLMConfig(**data.get('llm', {})),
                security=SecurityConfig(**data.get('security', {})),
                features=FeatureConfig(**data.get('features', {})),
                paths=PathConfig(**data.get('paths', {})),
                whatsapp=WhatsAppConfig(**data.get('whatsapp', {})),
                google=GoogleConfig(**data.get('google', {})),
                telegram_token=data.get('telegram_token', ''),
                telegram_user_id=data.get('telegram_user_id', ''),
                telegram_allowed_users=data.get('telegram_allowed_users', []),
                first_run=False,
                version=data.get('version', '1.0.0')
            )
            return True
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if minimum required configuration is present."""
        return len(self.config.llm.api_keys) > 0
    
    def get_active_provider(self) -> tuple[str, Optional[str]]:
        """
        Get the currently active provider and its key.
        Returns (provider_name, api_key).
        """
        provider = self.config.llm.provider.lower()
        key = self.config.get_api_key(provider)
        
        # If primary provider has no key, try to find one with a key
        if not key:
            for p, k in self.config.llm.api_keys.items():
                if k:
                    return p, k
        
        return provider, key
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return getattr(self.config.features, feature_name, False)


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    return _config_manager
