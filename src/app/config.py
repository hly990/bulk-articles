"""
Application configuration and settings
"""

import os
import json
import logging
from pathlib import Path

class Config:
    """Application configuration class"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "app": {
            "name": "YT-Article Craft",
            "theme": "default",  # default, light, dark
            "language": "en",
            "save_path": str(Path.home() / "YT-Article-Craft"),
            "auto_save": True,
            "auto_save_interval": 300,  # seconds
            "restore_session": True,
            "show_notifications": True,
            "confirm_exit": True
        },
        "api": {
            "openai_api_key": "",
            "medium_api_key": "",
            "wordpress_api_key": "",
            "deepl_api_key": ""
        },
        "ui": {
            "font_family": "Arial",
            "font_size": 10,
            "editor_font_family": "Menlo",
            "editor_font_size": 12,
            "window_width": 1280,
            "window_height": 800,
            "task_dock_width": 250,
            "preview_pane_width": 350,
            "splitter_sizes": [250, 680, 350],  # Default sizes for the three panes
            "task_dock_min_width": 200,
            "task_dock_max_width": 400,
            "preview_pane_min_width": 300,
            "preview_pane_max_width": 600,
            "editor_pane_min_width": 400
        },
        "editor": {
            "spell_check": True,
            "show_word_count": True,
            "auto_format": False,
            "line_numbers": True,
            "syntax_highlighting": True
        },
        "advanced": {
            "debug_mode": False,
            "log_level": "INFO",
            "max_recent_files": 10,
            "max_undo_steps": 100,
            "gpu_acceleration": True
        }
    }
    
    def __init__(self):
        """Initialize configuration"""
        self.config_dir = Path.home() / ".yt-article-craft"
        self.config_file = self.config_dir / "config.json"
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=str(self.config_dir / 'app.log'),
            filemode='a'
        )
        self.logger = logging.getLogger("Config")
        
        # Create config directory if it doesn't exist
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating config directory: {e}")
        
        # Load configuration if it exists
        if self.config_file.exists():
            self.load()
        else:
            # Create default configuration file
            self.save()
            self.logger.info("Created default configuration file")
    
    def load(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                
            # Update configuration with loaded values, preserving defaults for missing keys
            self._merge_configs(self.config, loaded_config)
            self.logger.info("Configuration loaded successfully")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            # Create backup of corrupted file
            backup_file = self.config_file.with_suffix(".json.bak")
            try:
                os.rename(self.config_file, backup_file)
                self.logger.info(f"Corrupted config file backed up to {backup_file}")
                # Create new default config
                self.save()
                self.logger.info("Created new default configuration file")
            except Exception as e:
                self.logger.error(f"Error backing up corrupted config file: {e}")
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
    
    def _merge_configs(self, target, source):
        """
        Recursively merge source config into target config
        
        Args:
            target (dict): Target configuration dictionary
            source (dict): Source configuration dictionary
        """
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    # Recursively merge dictionaries
                    self._merge_configs(target[key], value)
                else:
                    # Update value
                    target[key] = value
            else:
                # Add new key
                target[key] = value
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, section, key, default=None):
        """
        Get configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            return self.config[section][key]
        except KeyError:
            # If section exists but key doesn't, add default value
            if section in self.config:
                if key in self.DEFAULT_CONFIG.get(section, {}):
                    # Use default from DEFAULT_CONFIG if available
                    self.config[section][key] = self.DEFAULT_CONFIG[section][key]
                    return self.config[section][key]
            return default
    
    def set(self, section, key, value):
        """
        Set configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            value: Value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            return True
        except Exception as e:
            self.logger.error(f"Error setting configuration value: {e}")
            return False
    
    def get_all(self):
        """
        Get entire configuration
        
        Returns:
            dict: Configuration dictionary
        """
        return self.config
    
    def reset_to_defaults(self):
        """
        Reset configuration to defaults
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config = self.DEFAULT_CONFIG.copy()
            return self.save()
        except Exception as e:
            self.logger.error(f"Error resetting configuration: {e}")
            return False
    
    def reset_section(self, section):
        """
        Reset a specific section to defaults
        
        Args:
            section (str): Configuration section to reset
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if section in self.DEFAULT_CONFIG:
                self.config[section] = self.DEFAULT_CONFIG[section].copy()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error resetting section {section}: {e}")
            return False 