"""
Application constants

This module defines constants used throughout the application
"""

# Task status constants
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Article tone constants
TONE_PROFESSIONAL = "professional"
TONE_CASUAL = "casual"
TONE_TECHNICAL = "technical"
TONE_ENTHUSIASTIC = "enthusiastic"
TONE_FORMAL = "formal"
TONE_INFORMATIVE = "informative"

# Database constants
DEFAULT_DB_FILENAME = "ytarticlecraft.db"
DB_VERSION = 1

# UI constants
DEFAULT_FONT_SIZE = 12
DEFAULT_FONT_FAMILY = "Arial"

# Task status display names (for UI)
STATUS_DISPLAY_NAMES = {
    STATUS_PENDING: "Pending",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED: "Completed",
    STATUS_FAILED: "Failed"
}

# Valid task status values
VALID_STATUSES = [
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_FAILED
]

# Template tone constants
TONE_STORYTELLING = "storytelling"
TONE_EDUCATIONAL = "educational"

# Valid template tones
VALID_TONES = [
    TONE_PROFESSIONAL,
    TONE_CASUAL,
    TONE_STORYTELLING,
    TONE_TECHNICAL,
    TONE_EDUCATIONAL
]

# Tone display names (for UI)
TONE_DISPLAY_NAMES = {
    TONE_PROFESSIONAL: "Professional",
    TONE_CASUAL: "Casual",
    TONE_STORYTELLING: "Storytelling",
    TONE_TECHNICAL: "Technical",
    TONE_EDUCATIONAL: "Educational"
}

# YouTube URL patterns
YOUTUBE_URL_PATTERN = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'

# Default application settings
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_EDITOR_FONT = "DejaVu Sans Mono"
DEFAULT_PREVIEW_FONT = "DejaVu Sans"

# File paths
CONFIG_FILE_PATH = "config.json"
DEFAULT_SAVE_DIRECTORY = "saved_tasks"

# UI constants
UI_MAIN_TITLE = "YT-Article Craft"
UI_STATUS_READY = "Ready"
UI_STATUS_PROCESSING = "Processing..."

# Default style sheet
DEFAULT_STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #f5f5f5;
}

QMenuBar, QStatusBar {
    background-color: #ffffff;
}

QDockWidget::title {
    background-color: #e0e0e0;
    padding: 5px;
}

QSplitter::handle {
    background-color: #cccccc;
}

QListView, QTreeView {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 3px;
}

QPushButton {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #0069d9;
}

QPushButton:pressed {
    background-color: #0062cc;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #999999;
}
""" 