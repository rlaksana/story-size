import yaml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "llm": {
        "endpoint": "https://api.z.ai/api/anthropic/v1/messages",
        "api_key_env": "ZAI_API_KEY",
        "model": "glm-4.6",
    },
    "weights": {
        "DC": 1,
        "IC": 1,
        "IB": 1,
        "DS": 1,
        "NR": 1,
    },
    "mapping": {
        "sp1_max": 7,
        "sp2_max": 10,
        "sp3_max": 13,
        "sp5_max": 16,
        "sp8_max": 20,
        "sp13_max": 25,
    },
}

def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Loads the configuration from a YAML file.
    """
    if config_path and config_path.is_file():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
        
        # Deep merge user config into default config
        config = DEFAULT_CONFIG.copy()
        for key, value in user_config.items():
            if isinstance(value, dict) and isinstance(config.get(key), dict):
                config[key].update(value)
            else:
                config[key] = value
        return config
    return DEFAULT_CONFIG
