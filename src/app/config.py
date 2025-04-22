"""
Application configuration and settings
"""

import os
import json
from pathlib import Path

class Config:
    """Application configuration class"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "app": {
            "name": "YT-Article Craft",
            "theme": "default",
            "language": "en",
            "save_path": str(Path.home() / "YT-Article-Craft"),
            "auto_save": True,
            "auto_save_interval": 300,  # seconds
        },
        "api": {
            "openai_api_key": "",
            "medium_api_key": "",
            "wordpress_api_key": "",
            "deepl_api_key": ""
        },
        "ui": {
            "font_family": "Segoe UI",
            "font_size": 10,
            "editor_font_family": "Consolas",
            "editor_font_size": 12,
            "window_width": 1280,
            "window_height": 800,
            "task_dock_width": 250,
            "preview_pane_width": 350,
            "splitter_sizes": [250, 680, 350]  # Default sizes for the three panes
        }
    }
    
    def __init__(self):
        """Initialize configuration"""
        self.config_dir = Path.home() / ".yt-article-craft"
        self.config_file = self.config_dir / "config.json"
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load configuration if it exists
        if self.config_file.exists():
            self.load()
        else:
            # Create default configuration file
            self.save()
    
    def load(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                
            # Update configuration with loaded values, preserving defaults for missing keys
            for section in self.config:
                if section in loaded_config:
                    for key in self.config[section]:
                        if key in loaded_config[section]:
                            self.config[section][key] = loaded_config[section][key]
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def get(self, section, key, default=None):
        """Get configuration value"""
        try:
            return self.config[section][key]
        except KeyError:
            return default
    
    def set(self, section, key, value):
        """Set configuration value"""
        try:
            self.config[section][key] = value
            return True
        except KeyError:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return True
    
    def get_all(self):
        """Get entire configuration"""
        return self.config 