#!/usr/bin/env python3
"""
YT-Article Craft - Main application entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from app.config import Config
from views.main_window import MainWindow

def main():
    """Main application entry point"""
    
    # Set application information
    QCoreApplication.setApplicationName("YT-Article Craft")
    QCoreApplication.setOrganizationName("YT-Article Craft")
    QCoreApplication.setApplicationVersion("0.1.0")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Load configuration
    config = Config()
    
    # Show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 