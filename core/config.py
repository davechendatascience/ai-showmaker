"""
Enhanced Configuration Manager for AI-Showmaker

Provides centralized configuration management with support for
multiple configuration sources and environment-specific settings.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from .exceptions import ConfigurationError


class ConfigManager:
    """
    Centralized configuration management for AI-Showmaker.
    
    Supports multiple configuration sources with priority:
    1. Environment variables (highest priority)
    2. .env file 
    3. config files (JSON/YAML)
    4. Default values (lowest priority)
    """
    
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.config_data: Dict[str, Any] = {}
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load configuration from all sources."""
        # Load from .env file first
        self._load_env_file()
        
        # Load from config files
        self._load_config_files()
        
        # Load from environment variables (highest priority)
        self._load_environment_variables()
        
        # Set defaults for missing values
        self._set_defaults()
        
        # Validate required configuration
        self._validate_configuration()
    
    def _load_env_file(self) -> None:
        """Load configuration from .env file."""
        env_file = self.config_dir / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
    
    def _load_config_files(self) -> None:
        """Load configuration from JSON files."""
        # Load from secrets.json (legacy support)
        secrets_file = self.config_dir / 'secrets' / 'secrets.json'
        if secrets_file.exists():
            try:
                with open(secrets_file, 'r') as f:
                    secrets = json.load(f)
                    self.config_data.update(secrets)
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"Invalid JSON in secrets.json: {str(e)}")
    
    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables."""
        env_vars = {
            'inference_net_key': 'INFERENCE_DOT_NET_KEY',
            'inference_net_base_url': 'INFERENCE_NET_BASE_URL',
            'inference_net_model': 'INFERENCE_NET_MODEL',
            'aws_host': 'AWS_HOST', 
            'aws_user': 'AWS_USER',
            'pem_path': 'PEM_PATH',
            'log_level': 'LOG_LEVEL',
            'max_retries': 'MAX_RETRIES',
            'timeout_seconds': 'TIMEOUT_SECONDS'
        }
        
        for config_key, env_key in env_vars.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                # Try to convert to appropriate type
                self.config_data[config_key] = self._convert_value(value)
    
    def _set_defaults(self) -> None:
        """Set default values for missing configuration."""
        defaults = {
            'inference_net_base_url': 'https://api.inference.net/v1',
            'inference_net_model': 'mistralai/mistral-nemo-12b-instruct/fp-8',
            'aws_host': 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com',
            'aws_user': 'ec2-user',
            'pem_path': 'secrets/ai-showmaker.pem',
            'log_level': 'INFO',
            'max_retries': 3,
            'timeout_seconds': 30,
            'connection_pool_size': 5,
            'connection_timeout': 300
        }
        
        for key, value in defaults.items():
            if key not in self.config_data:
                self.config_data[key] = value
    
    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _validate_configuration(self) -> None:
        """Validate that required configuration is present."""
        required_keys = ['inference_net_key', 'inference_net_base_url', 'inference_net_model']
        
        missing_keys = []
        for key in required_keys:
            if key not in self.config_data or not self.config_data[key]:
                missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing_keys)}"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config_data[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self.config_data.copy()
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server-specific configuration."""
        return {
            'aws_host': self.get('aws_host'),
            'aws_user': self.get('aws_user'),
            'pem_path': self.get('pem_path'),
            'connection_pool_size': self.get('connection_pool_size'),
            'connection_timeout': self.get('connection_timeout')
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration."""
        return {
            'inference_net_key': self.get('inference_net_key'),
            'inference_net_base_url': self.get('inference_net_base_url'),
            'inference_net_model': self.get('inference_net_model'),
            'max_retries': self.get('max_retries'),
            'timeout_seconds': self.get('timeout_seconds')
        }
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return self.get('environment', 'development').lower() == 'development'
    
    def __str__(self) -> str:
        """String representation of configuration (excluding sensitive data)."""
        safe_config = self.config_data.copy()
        # Mask sensitive values
        sensitive_keys = ['api_key', 'password', 'token']
        for key in safe_config:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_config[key] = '*' * 8
        
        return json.dumps(safe_config, indent=2)