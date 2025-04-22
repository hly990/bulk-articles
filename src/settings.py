"""
Settings manager for the application.
Manages loading, saving and accessing application settings.
"""
from PyQt5.QtCore import QObject, QSettings, pyqtSignal

class Settings(QObject):
    """
    Manages application settings with save/load functionality.
    Uses QSettings for persistent storage.
    """
    
    # Signal emitted when settings are changed
    settings_changed = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize settings manager"""
        super().__init__()
        
        # Initialize QSettings
        self.qsettings = QSettings("B2B", "BulkArticles")
        
        # Default settings
        self.default_settings = {
            # Appearance
            "theme": "System",
            "font_family": "Arial",
            "font_size": 11,
            
            # Editor
            "autosave_interval": 5,  # minutes (0 = disabled)
            "spell_check": True,
            "show_word_count": True,
            
            # Behavior
            "restore_session": True,
            "show_notifications": True,
            "confirm_exit": True,
            
            # Window state
            "window_width": 1200,
            "window_height": 800,
            "window_maximized": False,
            
            # Panel sizes
            "article_list_width": 300,
            "editor_width": 600
        }
        
        # Current settings (loaded from QSettings or defaults)
        self.current_settings = {}
        
        # Load settings
        self.load_settings()
    
    def load_settings(self):
        """
        Load settings from QSettings.
        Fall back to default values if not found.
        """
        # Start with default settings
        self.current_settings = self.default_settings.copy()
        
        # Load all keys from QSettings
        self.qsettings.beginGroup("")
        keys = self.qsettings.childKeys()
        self.qsettings.endGroup()
        
        # Override defaults with stored values
        for key in keys:
            if key in self.current_settings:
                value = self.qsettings.value(key, self.default_settings[key])
                
                # Convert to correct type based on default value type
                default_type = type(self.default_settings[key])
                if default_type == bool:
                    # Handle bool conversion from QSettings string
                    if isinstance(value, str):
                        value = value.lower() == 'true'
                    else:
                        value = bool(value)
                elif default_type == int:
                    value = int(value)
                elif default_type == float:
                    value = float(value)
                
                self.current_settings[key] = value
    
    def save_settings(self):
        """Save current settings to QSettings"""
        for key, value in self.current_settings.items():
            self.qsettings.setValue(key, value)
        
        # Ensure settings are written to storage
        self.qsettings.sync()
    
    def get(self, key, default=None):
        """
        Get a setting value
        
        Args:
            key (str): Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default if not found
        """
        return self.current_settings.get(key, default)
    
    def set(self, key, value):
        """
        Set a setting value
        
        Args:
            key (str): Setting key
            value: Setting value
        """
        if key in self.current_settings and self.current_settings[key] != value:
            self.current_settings[key] = value
            self.settings_changed.emit({key: value})
    
    def update(self, settings_dict):
        """
        Update multiple settings at once
        
        Args:
            settings_dict (dict): Dictionary of settings to update
        """
        changed = {}
        for key, value in settings_dict.items():
            if key in self.current_settings and self.current_settings[key] != value:
                self.current_settings[key] = value
                changed[key] = value
        
        if changed:
            self.settings_changed.emit(changed)
            self.save_settings()
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.current_settings = self.default_settings.copy()
        self.save_settings()
        self.settings_changed.emit(self.current_settings)
    
    def get_all(self):
        """
        Get all current settings
        
        Returns:
            dict: All current settings
        """
        return self.current_settings.copy() 