"""
Steam Screenshot Utils - Configuration Manager

Handles configuration settings for the SSU GUI application.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class SSUConfig:
    """Configuration data class for SSU GUI."""

    # Default operation settings
    dry_run_default: bool = False
    force_rename_default: bool = False

    # Window settings
    window_width: int = 900
    window_height: int = 700

    # Theme settings
    theme: str = "dark"

    # Path settings
    paths: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            "dry_run_default": self.dry_run_default,
            "force_rename_default": self.force_rename_default,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "theme": self.theme,
            "paths": self.paths
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SSUConfig':
        """Create config from dictionary."""
        return cls(
            dry_run_default=data.get("dry_run_default", False),
            force_rename_default=data.get("force_rename_default", False),
            window_width=data.get("window_width", 900),
            window_height=data.get("window_height", 700),
            theme=data.get("theme", "dark"),
            paths=data.get("paths", {})
        )


class ConfigManager:
    """Manages configuration persistence and access."""

    def __init__(self, config_file: str = "ssu_config.json"):
        self.config_file = Path(config_file)
        self._config: SSUConfig = None
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure the configuration directory exists."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> SSUConfig:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return SSUConfig.from_dict(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file: {e}")
                return SSUConfig()
        else:
            return SSUConfig()

    def _save_config(self):
        """Save configuration to file."""
        if self._config:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"Warning: Could not save config file: {e}")

    @property
    def config(self) -> SSUConfig:
        """Get the current configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def load_config(self) -> SSUConfig:
        """Load configuration from file."""
        return self._load_config()

    def save_config(self):
        """Save the current configuration."""
        self._save_config()

    def update_path(self, path_type: str, path: str):
        """Update a path in the configuration."""
        self.config.paths[path_type] = path
        self._save_config()

    def get_path(self, path_type: str, default: str = "") -> str:
        """Get a path from the configuration."""
        return self.config.paths.get(path_type, default)

    def set_window_size(self, width: int, height: int):
        """Update window size settings."""
        self.config.window_width = width
        self.config.window_height = height
        self._save_config()

    def set_theme(self, theme: str):
        """Update theme setting."""
        self.config.theme = theme
        self._save_config()

    def set_default_options(self, dry_run: bool = None, force_rename: bool = None):
        """Update default operation options."""
        if dry_run is not None:
            self.config.dry_run_default = dry_run
        if force_rename is not None:
            self.config.force_rename_default = force_rename
        self._save_config()


# Global configuration manager instance
config_manager = ConfigManager()
