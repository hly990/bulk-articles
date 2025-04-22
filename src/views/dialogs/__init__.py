"""
Dialog module for YT-Article Craft

This module contains all dialog classes used in the application.
"""

from .settings_dialog import SettingsDialog
from .new_task_dialog import NewTaskDialog
from .template_dialog import TemplateDialog
from .about_dialog import AboutDialog

__all__ = [
    'SettingsDialog',
    'NewTaskDialog',
    'TemplateDialog',
    'AboutDialog'
] 