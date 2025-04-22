"""
Application constants
"""

# Task statuses
STATUS_PENDING = "pending"
STATUS_DOWNLOADING = "downloading"
STATUS_TRANSCRIBING = "transcribing"
STATUS_EXTRACTING_KEYFRAMES = "extracting_keyframes"
STATUS_GENERATING_ARTICLE = "generating_article"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Article templates
TONE_PROFESSIONAL = "professional"
TONE_CASUAL = "casual"
TONE_STORYTELLING = "storytelling"
TONE_TECHNICAL = "technical"
TONE_EDUCATIONAL = "educational"

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