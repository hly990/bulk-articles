"""
New Task Dialog

Dialog for creating a new video processing task
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSlot


class NewTaskDialog(QDialog):
    """Dialog for creating a new video processing task"""
    
    def __init__(self, parent=None):
        """Initialize the dialog"""
        super().__init__(parent)
        
        self.setWindowTitle("New Task")
        self.setMinimumWidth(500)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        
        # Title field
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter task title")
        form_layout.addRow("Title:", self.title_edit)
        
        # Video URL field
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter YouTube URL")
        form_layout.addRow("Video URL:", self.url_edit)
        
        # Language selection
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Chinese", "Spanish", "French", "German"])
        form_layout.addRow("Language:", self.language_combo)
        
        # Template selection
        self.template_combo = QComboBox()
        self.template_combo.addItem("None")
        # Add templates here (to be loaded from database)
        form_layout.addRow("Template:", self.template_combo)
        
        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter task description (optional)")
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)
        
        # Add form to main layout
        main_layout.addLayout(form_layout)
        
        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Create and attach buttons
        main_layout.addWidget(self.button_box)
        
        # Connect signals
        self.title_edit.textChanged.connect(self._validate_inputs)
        self.url_edit.textChanged.connect(self._validate_inputs)
        
        # Initial validation
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate user inputs and enable/disable OK button"""
        # Check if title and URL are not empty
        title_valid = bool(self.title_edit.text().strip())
        url_valid = bool(self.url_edit.text().strip())
        
        # Enable/disable OK button
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            title_valid and url_valid
        )
    
    def get_task_data(self):
        """Get the task data from the dialog inputs
        
        Returns:
            dict: Task data dictionary
        """
        return {
            'title': self.title_edit.text().strip(),
            'url': self.url_edit.text().strip(),
            'language': self.language_combo.currentText().lower(),
            'description': self.description_edit.toPlainText().strip(),
            'template_id': None if self.template_combo.currentIndex() == 0 else self.template_combo.currentData()
        } 