"""
Centralized configuration for AgenticBobs.

This module provides a single source of truth for all configuration values
throughout the application, eliminating hardcoded values and reducing sprawl.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AIConfig:
    """Configuration for AI/LLM services."""
    
    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_url: str = "http://localhost:11434/v1"
    ollama_timeout: float = 120.0
    
    # Model configuration
    default_small_model: str = "qwen3:4b"
    default_large_model: str = "qwen3:8b" 
    default_model: str = "gpt-oss:20b"  # Legacy compatibility
    
    # API configuration
    api_key: str = ""
    
    @classmethod
    def from_environment(cls) -> 'AIConfig':
        """Create configuration from environment variables."""
        return cls(
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_api_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
            ollama_timeout=float(os.environ.get("OLLAMA_TIMEOUT", "120.0")),
            default_small_model=os.environ.get("SMALL_MODEL", "qwen3:4b"),
            default_large_model=os.environ.get("LARGE_MODEL", "qwen3:8b"),
            default_model=os.environ.get("DEFAULT_MODEL", "gpt-oss:20b"),
            api_key=os.environ.get("LLM_API_KEY", ""),
        )


@dataclass
class APIConfig:
    """Configuration for FastAPI backend."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = None
    debug: bool = False
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = [
                "http://localhost:5173",  # Vite dev server
                "http://localhost:5174",  # Vite dev server alternate
                "http://localhost:3000",  # React/Vue dev server
            ]
    
    @classmethod
    def from_environment(cls) -> 'APIConfig':
        """Create configuration from environment variables."""
        cors_origins_str = os.environ.get("CORS_ORIGINS")
        cors_origins = None
        if cors_origins_str:
            # Handle both JSON array and comma-separated string
            try:
                import json
                cors_origins = json.loads(cors_origins_str)
            except (json.JSONDecodeError, ValueError):
                cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
        
        return cls(
            host=os.environ.get("API_HOST", "0.0.0.0"),
            port=int(os.environ.get("API_PORT", "8000")),
            cors_origins=cors_origins,
            debug=os.environ.get("DEBUG", "").lower() in ("true", "1", "yes"),
        )


@dataclass
class StreamlitConfig:
    """Configuration for Streamlit frontend."""
    
    host: str = "localhost"
    port: int = 8501
    debug: bool = False
    
    @classmethod
    def from_environment(cls) -> 'StreamlitConfig':
        """Create configuration from environment variables."""
        return cls(
            host=os.environ.get("STREAMLIT_HOST", "localhost"),
            port=int(os.environ.get("STREAMLIT_PORT", "8501")),
            debug=os.environ.get("DEBUG", "").lower() in ("true", "1", "yes"),
        )


@dataclass
class VueConfig:
    """Configuration for Vue.js frontend."""
    
    host: str = "localhost"
    port: int = 5173
    api_base_url: str = "http://localhost:8000/api"
    
    @classmethod
    def from_environment(cls) -> 'VueConfig':
        """Create configuration from environment variables."""
        return cls(
            host=os.environ.get("VUE_HOST", "localhost"),
            port=int(os.environ.get("VUE_PORT", "5173")),
            api_base_url=os.environ.get("VUE_API_BASE", "http://localhost:8000/api"),
        )


@dataclass
class ProcessConfig:
    """Configuration for process generation and validation."""
    
    default_process_type: str = "BPMN"
    validation_enabled: bool = True
    layout_algorithm: str = "dot"  # For BPMN layout
    
    @classmethod
    def from_environment(cls) -> 'ProcessConfig':
        """Create configuration from environment variables."""
        return cls(
            default_process_type=os.environ.get("DEFAULT_PROCESS_TYPE", "BPMN"),
            validation_enabled=os.environ.get("VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes"),
            layout_algorithm=os.environ.get("LAYOUT_ALGORITHM", "dot"),
        )


@dataclass
class AgenticBobsConfig:
    """Main configuration container for the entire application."""
    
    ai: AIConfig
    api: APIConfig
    streamlit: StreamlitConfig
    vue: VueConfig
    process: ProcessConfig
    
    @classmethod
    def from_environment(cls) -> 'AgenticBobsConfig':
        """Create complete configuration from environment variables."""
        return cls(
            ai=AIConfig.from_environment(),
            api=APIConfig.from_environment(),
            streamlit=StreamlitConfig.from_environment(),
            vue=VueConfig.from_environment(),
            process=ProcessConfig.from_environment(),
        )
    
    @classmethod
    def default(cls) -> 'AgenticBobsConfig':
        """Create configuration with all default values."""
        return cls(
            ai=AIConfig(),
            api=APIConfig(),
            streamlit=StreamlitConfig(),
            vue=VueConfig(),
            process=ProcessConfig(),
        )


# Global configuration instance
# This will be initialized when the module is imported
_config: Optional[AgenticBobsConfig] = None


def get_config() -> AgenticBobsConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AgenticBobsConfig.from_environment()
    return _config


def set_config(config: AgenticBobsConfig) -> None:
    """Set the global configuration instance (useful for testing)."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to load from environment again."""
    global _config
    _config = None


# Convenience functions for common configuration access
def get_ai_config() -> AIConfig:
    """Get AI configuration."""
    return get_config().ai


def get_api_config() -> APIConfig:
    """Get API configuration."""
    return get_config().api


def get_streamlit_config() -> StreamlitConfig:
    """Get Streamlit configuration."""
    return get_config().streamlit


def get_vue_config() -> VueConfig:
    """Get Vue configuration."""
    return get_config().vue


def get_process_config() -> ProcessConfig:
    """Get process configuration."""
    return get_config().process