"""
Template Dialog

Dialog for creating and editing article templates
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QDialogButtonBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSlot


class TemplateDialog(QDialog):
    """Dialog for creating and editing article templates"""
    
    def __init__(self, parent=None, template_data=None):
        """Initialize the dialog
        
        Args:
            parent: Parent widget
            template_data: Optional dictionary with template data for editing
        """
        super().__init__(parent)
        
        self.template_data = template_data or {}
        
        self.setWindowTitle("Template" if template_data else "New Template")
        self.setMinimumSize(600, 500)
        
        self._init_ui()
        
        # Fill data if editing existing template
        if self.template_data:
            self._fill_template_data()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Tabs
        self.tab_widget = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        # Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter template name")
        general_layout.addRow("Name:", self.name_edit)
        
        # Tone selection
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([
            "Professional", "Casual", "Technical", "Enthusiastic", 
            "Formal", "Informative", "Storytelling", "Educational"
        ])
        general_layout.addRow("Tone:", self.tone_combo)
        
        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter template description")
        self.description_edit.setMaximumHeight(100)
        general_layout.addRow("Description:", self.description_edit)
        
        # Tags field
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Enter tags separated by commas")
        general_layout.addRow("Tags:", self.tags_edit)
        
        self.tab_widget.addTab(general_tab, "General")
        
        # Content tab
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)
        
        # Template content editor
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Enter template content with placeholders")
        content_layout.addWidget(self.content_edit)
        
        self.tab_widget.addTab(content_tab, "Content")
        
        # Style tab
        style_tab = QWidget()
        style_layout = QFormLayout(style_tab)
        
        # Font selection
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Default", "Arial", "Times New Roman", "Georgia", "Verdana"])
        style_layout.addRow("Font:", self.font_combo)
        
        # Font size selection
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["Default", "Small", "Medium", "Large"])
        style_layout.addRow("Font Size:", self.font_size_combo)
        
        # Custom CSS editor
        self.css_edit = QTextEdit()
        self.css_edit.setPlaceholderText("Enter custom CSS (optional)")
        style_layout.addRow("Custom CSS:", self.css_edit)
        
        self.tab_widget.addTab(style_tab, "Style")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
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
        self.name_edit.textChanged.connect(self._validate_inputs)
        self.content_edit.textChanged.connect(self._validate_inputs)
        
        # Initial validation
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate user inputs and enable/disable OK button"""
        # Check if name and content are not empty
        name_valid = bool(self.name_edit.text().strip())
        content_valid = bool(self.content_edit.toPlainText().strip())
        
        # Enable/disable OK button
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            name_valid and content_valid
        )
    
    def _fill_template_data(self):
        """Fill dialog fields with existing template data"""
        if not self.template_data:
            return
            
        # Fill general tab
        self.name_edit.setText(self.template_data.get('name', ''))
        
        tone = self.template_data.get('tone', '')
        index = self.tone_combo.findText(tone, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.tone_combo.setCurrentIndex(index)
            
        self.description_edit.setText(self.template_data.get('description', ''))
        
        tags = self.template_data.get('tags', [])
        if isinstance(tags, list):
            self.tags_edit.setText(', '.join(tags))
        
        # Fill content tab
        self.content_edit.setText(self.template_data.get('content', ''))
        
        # Fill style tab
        css = self.template_data.get('css', '')
        self.css_edit.setText(css)
    
    def get_template_data(self):
        """Get the template data from the dialog inputs
        
        Returns:
            dict: Template data dictionary
        """
        # Parse tags
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        
        return {
            'name': self.name_edit.text().strip(),
            'tone': self.tone_combo.currentText(),
            'description': self.description_edit.toPlainText().strip(),
            'tags': tags,
            'content': self.content_edit.toPlainText().strip(),
            'css': self.css_edit.toPlainText().strip()
        } 