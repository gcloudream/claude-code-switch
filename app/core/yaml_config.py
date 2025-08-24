"""YAML configuration loader with environment variable substitution"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class YamlConfigLoader:
    """Load and parse YAML configuration with environment variable substitution"""
    
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration loader
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
    
    def _substitute_env_vars(self, value: Any) -> Any:
        """Recursively substitute environment variables in configuration values
        
        Args:
            value: Configuration value to process
            
        Returns:
            Processed value with environment variables substituted
        """
        if isinstance(value, str):
            # Find all environment variable references
            matches = self.ENV_VAR_PATTERN.findall(value)
            for match in matches:
                env_var = match.strip()
                env_value = os.environ.get(env_var, "")
                if not env_value and env_var in ["ADMIN_PASSWORD", "UPSTREAM_API_KEY", "SECRET_KEY"]:
                    # Critical variables should raise error if not set
                    raise ValueError(f"Environment variable {env_var} is not set")
                value = value.replace(f"${{{match}}}", env_value)
            return value
        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        else:
            return value
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file
        
        Returns:
            Parsed configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValueError: If required environment variables are not set
        """
        if self._config is not None:
            return self._config
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Substitute environment variables
        self._config = self._substitute_env_vars(config)
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key
        
        Args:
            key: Configuration key in dot notation (e.g., "app.name")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._config is None:
            self.load()
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_upstream_config(self) -> Dict[str, Any]:
        """Get upstream API configuration
        
        Returns:
            Upstream API configuration dictionary
        """
        return self.get("upstream.primary", {})
    
    def get_admin_config(self) -> Dict[str, str]:
        """Get admin configuration
        
        Returns:
            Admin configuration dictionary
        """
        return self.get("admin", {})
    
    def get_rate_limit_config(self, tier: str = "default") -> Dict[str, int]:
        """Get rate limit configuration for a specific tier
        
        Args:
            tier: Rate limit tier (default, basic, premium, unlimited)
            
        Returns:
            Rate limit configuration dictionary
        """
        if tier == "default":
            return self.get("rate_limit.default", {"requests": 100, "period": 60})
        return self.get(f"rate_limit.by_tier.{tier}", self.get("rate_limit.default", {}))
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled
        
        Args:
            feature: Feature name
            
        Returns:
            True if feature is enabled, False otherwise
        """
        return self.get(f"features.{feature}", False)
    
    def reload(self) -> Dict[str, Any]:
        """Reload configuration from file
        
        Returns:
            Newly loaded configuration dictionary
        """
        self._config = None
        return self.load()


# Global configuration instance
yaml_config = YamlConfigLoader()