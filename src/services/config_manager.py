import os
import json
from dotenv import load_dotenv, find_dotenv
import logging
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

class ConfigManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Load .env file without clearing existing environment variables
            load_dotenv(find_dotenv(), override=True)
            self._runtime_config = {}
            self._initialized = True
            logger.debug("ConfigManager initialized")

    def set_config(self, key: str, value: str):
        """Set a configuration value that takes precedence over .env"""
        self._runtime_config[key] = value
        # Also update environment variable for compatibility
        os.environ[key] = str(value)
        logger.debug(f"Config set: {key}={self._mask_value(key, value)}")

    def get_config(self, key: str, default: str = None) -> str:
        """Get configuration value, prioritizing runtime config over .env"""
        value = self._runtime_config.get(key, os.getenv(key, default))
        
        # Special handling for CODE_GENERATION_PERSONA to ensure valid value
        if key == "CODE_GENERATION_PERSONA" and (not value or value.strip() == ""):
            value = "playwright_ts_code"  # Default to TypeScript if no valid value
        
        # Clean Azure OpenAI endpoint if that's what we're getting
        if key == 'AZURE_OPENAI_ENDPOINT':
            value = self._clean_azure_endpoint(value)
        
        # Special handling for Azure deployment name
        if key == 'AZURE_DEPLOYMENT_NAME':
            # First try to get explicit deployment name
            deployment_name = self._runtime_config.get('AZURE_DEPLOYMENT_NAME', os.getenv('AZURE_DEPLOYMENT_NAME'))
            if deployment_name:
                value = deployment_name
            else:
                # If no deployment name is set, use MODEL_NAME as fallback
                value = self._runtime_config.get('MODEL_NAME', os.getenv('MODEL_NAME', default))
            logger.debug(f"Using deployment name: {value}")
        
        logger.debug(f"Config get: {key}={self._mask_value(key, value)}")
        return value

    def update_from_ui(self, settings: dict):
        """Update multiple settings at once from UI"""
        logger.debug("Updating settings from UI")
        for key, value in settings.items():
            if value is not None:  # Only update if value is provided
                self.set_config(key, str(value))
        # Print configuration snapshot after update
        self.print_config_snapshot()

    def get_all_configs(self) -> dict:
        """Get all current configurations"""
        return self._runtime_config.copy()

    def get_config_snapshot(self) -> dict:
        """Get a snapshot of all configurations organized by category"""
        snapshot = {
            "Model Settings": {
                "Provider": self.get_config("MODEL_PROVIDER", "openai"),
                "Model Name": self.get_config("MODEL_NAME", "gpt-4"),
                "Use Vision": self.get_config("USE_VISION", "false"),
                "API Key": self._mask_api_key(self.get_config(f"{self.get_config('MODEL_PROVIDER', 'openai').upper()}_API_KEY", ""))
            },
            "Browser Settings": {
                "Type": self.get_config("BROWSER_TYPE", "local"),
                "Cloud Provider": self.get_config("BROWSER_CLOUD_PROVIDER", ""),
            },
            "General Settings": {
                "Code Generation Style": self.get_config("CODE_GENERATION_PERSONA", "playwright_py_code"),
                "Conversation Log Path": self.get_config("CONVERSATION_LOG_PATH", "logs/conversation.json")
            }
        }

        # Add cloud provider API key if using remote browser
        if self.get_config("BROWSER_TYPE", "local") == "remote":
            cloud_provider = self.get_config("BROWSER_CLOUD_PROVIDER", "")
            if cloud_provider:
                snapshot["Browser Settings"]["Cloud API Key"] = self._mask_api_key(
                    self.get_config(f"{cloud_provider.upper()}_API_KEY", "")
                )

        return snapshot

    def print_config_snapshot(self):
        """Print a formatted snapshot of all configurations"""
        snapshot = self.get_config_snapshot()
        logger.debug("\n=== Configuration Snapshot ===")
        logger.debug(json.dumps(snapshot, indent=2))
        logger.debug("============================\n")

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for secure logging"""
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return f"{api_key[:4]}...{api_key[-4:]}"

    def _mask_value(self, key: str, value: str) -> str:
        """Mask sensitive values for logging"""
        if key.endswith(('_API_KEY', '_KEY', 'API_KEY')):
            return self._mask_api_key(value)
        return value

    def _clean_azure_endpoint(self, endpoint):
        """Clean Azure OpenAI endpoint to ensure it's just the base URL."""
        if not endpoint:
            return endpoint
            
        try:
            # Parse the URL
            parsed = urlparse(endpoint)
            # Return just the scheme and netloc (base URL)
            cleaned = f"{parsed.scheme}://{parsed.netloc}"
            logger.debug(f"Cleaned Azure endpoint from '{endpoint}' to '{cleaned}'")
            return cleaned
        except Exception as e:
            logger.warning(f"Error cleaning Azure endpoint '{endpoint}': {str(e)}")
            return endpoint 