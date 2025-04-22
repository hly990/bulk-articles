"""
About Dialog

Dialog for displaying application information
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDialogButtonBox, QTextBrowser
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont


class AboutDialog(QDialog):
    """Dialog for displaying application information"""
    
    def __init__(self, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.setWindowTitle("About YT-Article Craft")
        self.setFixedSize(450, 400)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Header with logo and title
        header_layout = QHBoxLayout()
        
        # Logo (placeholder - would normally load from resources)
        logo_label = QLabel()
        logo_label.setFixedSize(64, 64)
        # logo_label.setPixmap(QPixmap(":/icons/app_logo.png").scaled(
        #     64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        # ))
        header_layout.addWidget(logo_label)
        
        # Title and version
        title_layout = QVBoxLayout()
        
        app_name = QLabel("YT-Article Craft")
        app_name.setFont(QFont("", 16, QFont.Weight.Bold))
        title_layout.addWidget(app_name)
        
        app_version = QLabel("Version 1.0.0")
        title_layout.addWidget(app_version)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Description
        description = QLabel("YT-Article Craft is a desktop application that automates " +
                            "the process of converting YouTube videos into well-structured " +
                            "articles with embedded keyframes.")
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Detailed info in a text browser
        info_browser = QTextBrowser()
        info_browser.setOpenExternalLinks(True)
        info_browser.setHtml("""
        <h3>Features</h3>
        <ul>
            <li>Download YouTube videos</li>
            <li>Transcribe videos to text</li>
            <li>Extract key frames at important moments</li>
            <li>Generate Medium-style articles</li>
            <li>Apply AI detection evasion techniques</li>
            <li>Publish to Medium and WordPress</li>
        </ul>
        
        <h3>Credits</h3>
        <p>Developed by YT-Article Craft Team</p>
        
        <h3>License</h3>
        <p>Copyright © 2023-2024 YT-Article Craft Team</p>
        <p>All rights reserved.</p>
        
        <p>Visit <a href="https://github.com/yourusername/yt-article-craft">GitHub Repository</a> for more information.</p>
        """)
        main_layout.addWidget(info_browser)
        
        # OK button
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        main_layout.addWidget(self.button_box) 