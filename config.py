import os
import json
from pathlib import Path

def load_config():
    """Load configuration from environment variables or files."""
    config = {}
    
    # Try to load from .env file first
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Load Google API key
    if 'GOOGLE_API_KEY' in os.environ:
        config['google_api_key'] = os.environ['GOOGLE_API_KEY']
    else:
        # Fallback to secrets.json for backward compatibility
        secrets_file = Path('secrets/secrets.json')
        if secrets_file.exists():
            with open(secrets_file, 'r') as f:
                secrets = json.load(f)
            config['google_api_key'] = secrets.get('GOOGLE_API_KEY')
    
    # Load AWS configuration
    config['aws_host'] = os.environ.get('AWS_HOST', 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com')
    config['aws_user'] = os.environ.get('AWS_USER', 'ec2-user')
    config['pem_path'] = os.environ.get('PEM_PATH', 'secrets/ai-showmaker.pem')
    
    return config

def get_config():
    """Get the configuration dictionary."""
    return load_config()