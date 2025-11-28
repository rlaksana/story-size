import yaml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "llm": {
        "endpoint": "https://api.z.ai/api/anthropic/v1/messages",
        "api_key_env": "ZAI_API_KEY",
        "model": "glm-4.6",
    },

    # Traditional factor weights (for backward compatibility)
    "weights": {
        "DC": 1,
        "IC": 1,
        "IB": 1,
        "DS": 1,
        "NR": 1,
    },

    # Traditional story point mapping
    "mapping": {
        "sp1_max": 7,
        "sp2_max": 10,
        "sp3_max": 13,
        "sp5_max": 16,
        "sp8_max": 20,
        "sp13_max": 25,
    },

    # Enhanced platform-aware configuration
    "directory_mapping": {
        # Default directory patterns for auto-detection
        "frontend_patterns": ["frontend", "fe", "web", "client", "src/app", "src/components", "src/views", "src/pages"],
        "backend_patterns": ["backend", "be", "server", "api", "src/api", "src/services", "src/controllers"],
        "mobile_patterns": ["mobile", "app", "ios", "android", "flutter", "react-native", "lib"],
        "devops_patterns": ["devops", "infra", "deployment", "docker", "k8s", "kubernetes", ".github", "ci-cd"]
    },

    "platform_detection": {
        "auto_detect_threshold": 0.7,  # Minimum confidence for auto-detection
        "file_pattern_weight": 0.6,    # Weight for file pattern detection
        "directory_name_weight": 0.4,  # Weight for directory name matching
        "min_files_for_platform": 2    # Minimum files to consider platform present
    },

    "platform_weights": {
        "frontend": {"base": 1.0, "ui_factor": 1.2, "integration_factor": 0.8},
        "backend": {"base": 1.0, "business_factor": 1.1, "data_factor": 1.3},
        "mobile": {"base": 1.0, "platform_factor": 1.4, "store_factor": 1.2},
        "devops": {"base": 0.8, "infra_factor": 1.0, "automation_factor": 1.1}
    },

    "platform_mapping": {
        # Platform-specific story point ranges
        "sp1_max": 5, "sp2_max": 8, "sp3_max": 12, "sp5_max": 16, "sp8_max": 20, "sp13_max": 25,

        # Platform complexity thresholds
        "frontend": {"sp1_max": 4, "sp2_max": 7, "sp3_max": 11, "sp5_max": 15, "sp8_max": 19},
        "backend": {"sp1_max": 5, "sp2_max": 8, "sp3_max": 12, "sp5_max": 17, "sp8_max": 22},
        "mobile": {"sp1_max": 4, "sp2_max": 7, "sp3_max": 10, "sp5_max": 14, "sp8_max": 18},
        "devops": {"sp1_max": 3, "sp2_max": 6, "sp3_max": 9, "sp5_max": 13, "sp8_max": 17}
    },

    "analysis_options": {
        "include_key_files_in_prompt": True,
        "max_key_files_per_platform": 5,
        "include_dependencies_analysis": True,
        "max_prompt_length": 8000,
        "temperature": 0.2,
        "max_tokens": 1500,
        "timeout_seconds": 30
    }
}

def load_config(config_path: Path = None) -> Dict[str, Any]:
    """
    Loads the configuration from a YAML file with deep merge support.

    Args:
        config_path: Path to custom configuration file

    Returns:
        Merged configuration dictionary
    """
    if config_path and config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config file '{config_path}': {e}")
            print("Using default configuration.")
            user_config = {}

        # Deep merge user config into default config
        config = deep_merge_dict(DEFAULT_CONFIG.copy(), user_config)

        # Validate critical configuration
        config = validate_config(config)

        return config

    return DEFAULT_CONFIG.copy()

def deep_merge_dict(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base_dict: Base dictionary to merge into
        update_dict: Dictionary with updates

    Returns:
        Deep merged dictionary
    """
    result = base_dict.copy()

    for key, value in update_dict.items():
        if key in result:
            if isinstance(value, dict) and isinstance(result[key], dict):
                # Recursively merge nested dictionaries
                result[key] = deep_merge_dict(result[key], value)
            else:
                # Override with new value
                result[key] = value
        else:
            # Add new key
            result[key] = value

    return result

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and fix critical configuration values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Validated configuration dictionary
    """
    # Validate LLM configuration
    if "llm" not in config:
        config["llm"] = DEFAULT_CONFIG["llm"].copy()
    else:
        llm_config = config["llm"]

        # Ensure required LLM fields exist
        if "endpoint" not in llm_config:
            llm_config["endpoint"] = DEFAULT_CONFIG["llm"]["endpoint"]
        if "api_key_env" not in llm_config:
            llm_config["api_key_env"] = DEFAULT_CONFIG["llm"]["api_key_env"]
        if "model" not in llm_config:
            llm_config["model"] = DEFAULT_CONFIG["llm"]["model"]

    # Validate platform mapping
    if "platform_mapping" not in config:
        config["platform_mapping"] = DEFAULT_CONFIG["platform_mapping"].copy()

    # Validate analysis options
    if "analysis_options" not in config:
        config["analysis_options"] = DEFAULT_CONFIG["analysis_options"].copy()

    # Ensure values are in reasonable ranges
    analysis_options = config["analysis_options"]
    if not (0.0 <= analysis_options.get("temperature", 0.2) <= 1.0):
        analysis_options["temperature"] = 0.2

    max_tokens = analysis_options.get("max_tokens", 1500)
    if not (100 <= max_tokens <= 8000):
        analysis_options["max_tokens"] = min(max(max_tokens, 100), 8000)

    return config

def get_platform_config(config: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """
    Get platform-specific configuration.

    Args:
        config: Global configuration
        platform: Platform name (frontend, backend, mobile, devops)

    Returns:
        Platform-specific configuration
    """
    platform_config = {
        "weights": config.get("platform_weights", {}).get(platform, {"base": 1.0}),
        "mapping": config.get("platform_mapping", {}).get(platform, {}),
        "patterns": config.get("directory_mapping", {}).get(f"{platform}_patterns", []),
        "detection_config": config.get("platform_detection", {})
    }

    return platform_config

def save_sample_config(output_path: Path):
    """
    Save a sample configuration file with all options documented.

    Args:
        output_path: Path to save the sample configuration
    """
    sample_config = {
        "# Story Size Estimator Configuration": None,
        "llm": {
            "# LLM API configuration": None,
            "endpoint": "https://api.z.ai/api/anthropic/v1/messages",
            "api_key_env": "ZAI_API_KEY",
            "model": "glm-4.6",
            "# Optional: Request timeout in seconds": None,
            "timeout": 30
        },

        "weights": {
            "# Traditional factor weights (1-5 scale)": None,
            "DC": 1,  # Domain Complexity
            "IC": 1,  # Implementation Complexity
            "IB": 1,  # Integration Breadth
            "DS": 1,  # Data/Schema Impact
            "NR": 1   # Non-Functional & Risk
        },

        "mapping": {
            "# Traditional story point mapping ranges": None,
            "sp1_max": 7,
            "sp2_max": 10,
            "sp3_max": 13,
            "sp5_max": 16,
            "sp8_max": 20,
            "sp13_max": 25
        },

        "platform_detection": {
            "# Platform auto-detection settings": None,
            "auto_detect_threshold": 0.7,
            "file_pattern_weight": 0.6,
            "directory_name_weight": 0.4,
            "min_files_for_platform": 2
        },

        "platform_mapping": {
            "# Platform-specific story point mapping": None,
            "sp1_max": 5, "sp2_max": 8, "sp3_max": 12, "sp5_max": 16, "sp8_max": 20, "sp13_max": 25,
            "frontend": {"sp1_max": 4, "sp2_max": 7, "sp3_max": 11, "sp5_max": 15, "sp8_max": 19},
            "backend": {"sp1_max": 5, "sp2_max": 8, "sp3_max": 12, "sp5_max": 17, "sp8_max": 22},
            "mobile": {"sp1_max": 4, "sp2_max": 7, "sp3_max": 10, "sp5_max": 14, "sp8_max": 18},
            "devops": {"sp1_max": 3, "sp2_max": 6, "sp3_max": 9, "sp5_max": 13, "sp8_max": 17}
        },

        "analysis_options": {
            "# Analysis behavior options": None,
            "include_key_files_in_prompt": True,
            "max_key_files_per_platform": 5,
            "include_dependencies_analysis": True,
            "temperature": 0.2,
            "max_tokens": 1500
        }
    }

    # Remove comment keys (those starting with #)
    clean_config = {k: v for k, v in sample_config.items() if not k.startswith("#")}
    for key, value in clean_config.items():
        if isinstance(value, dict):
            clean_config[key] = {k: v for k, v in value.items() if not k.startswith("#")}

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(clean_config, f, default_flow_style=False, indent=2)
        print(f"Sample configuration saved to: {output_path}")
    except Exception as e:
        print(f"Error saving sample configuration: {e}")
