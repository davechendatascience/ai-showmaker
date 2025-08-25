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
    
    # Load inference.net configuration
    config['inference_net_key'] = os.environ.get('INFERENCE_DOT_NET_KEY')
    config['inference_net_base_url'] = os.environ.get('INFERENCE_NET_BASE_URL', 'https://api.inference.net/v1')
    config['inference_net_model'] = os.environ.get('INFERENCE_NET_MODEL', 'mistralai/mistral-nemo-12b-instruct/fp-8')
    
    # Load AWS configuration
    config['aws_host'] = os.environ.get('AWS_HOST', 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com')
    config['aws_user'] = os.environ.get('AWS_USER', 'ec2-user')
    config['pem_path'] = os.environ.get('PEM_PATH', 'secrets/ai-showmaker.pem')
    
    return config

def get_config():
    """Get the configuration dictionary."""
    return load_config()