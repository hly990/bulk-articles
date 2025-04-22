"""
Editor Pane for YT-Article Craft
Provides rich text editing capabilities for articles
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QToolBar, QComboBox, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QTextOption, QTextCharFormat, QFont, QColor, 
    QTextCursor, QAction, QIcon
)

class EditorPane(QWidget):
    """Editor pane widget for editing article content"""
    
    def __init__(self):
        """Initialize the editor pane"""
        super().__init__()
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Initialize UI
        self._init_ui()
        
        # Add sample content (for development only)
        self._add_sample_content()
        
    def _init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        self._create_toolbar()
        
        # Create editor
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.editor.textChanged.connect(self._on_text_changed)
        
        # Set editor font
        font = QFont("Segoe UI", 11)
        self.editor.setFont(font)
        
        # Add editor to layout
        self.layout.addWidget(self.editor)
    
    def _create_toolbar(self):
        """Create the formatting toolbar"""
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.layout.addWidget(self.toolbar)
        
        # Add font family selector
        self.font_family = QComboBox()
        self.font_family.addItems([
            "Default", "Arial", "Helvetica", "Times New Roman", 
            "Courier New", "Verdana", "Georgia"
        ])
        self.font_family.currentTextChanged.connect(self._on_font_family_changed)
        self.toolbar.addWidget(self.font_family)
        
        # Add font size selector
        self.font_size = QComboBox()
        self.font_size.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "28", "36"])
        self.font_size.setCurrentText("11")
        self.font_size.currentTextChanged.connect(self._on_font_size_changed)
        self.toolbar.addWidget(self.font_size)
        
        self.toolbar.addSeparator()
        
        # Bold action
        self.bold_action = QAction("Bold", self)
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(self._on_bold_triggered)
        self.toolbar.addAction(self.bold_action)
        
        # Italic action
        self.italic_action = QAction("Italic", self)
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(self._on_italic_triggered)
        self.toolbar.addAction(self.italic_action)
        
        # Underline action
        self.underline_action = QAction("Underline", self)
        self.underline_action.setCheckable(True)
        self.underline_action.triggered.connect(self._on_underline_triggered)
        self.toolbar.addAction(self.underline_action)
        
        self.toolbar.addSeparator()
        
        # Align left action
        self.align_left_action = QAction("Align Left", self)
        self.align_left_action.triggered.connect(lambda: self._on_alignment_triggered(Qt.AlignmentFlag.AlignLeft))
        self.toolbar.addAction(self.align_left_action)
        
        # Align center action
        self.align_center_action = QAction("Align Center", self)
        self.align_center_action.triggered.connect(lambda: self._on_alignment_triggered(Qt.AlignmentFlag.AlignCenter))
        self.toolbar.addAction(self.align_center_action)
        
        # Align right action
        self.align_right_action = QAction("Align Right", self)
        self.align_right_action.triggered.connect(lambda: self._on_alignment_triggered(Qt.AlignmentFlag.AlignRight))
        self.toolbar.addAction(self.align_right_action)
        
        self.toolbar.addSeparator()
        
        # Insert image action
        self.insert_image_action = QAction("Insert Image", self)
        self.insert_image_action.triggered.connect(self._on_insert_image)
        self.toolbar.addAction(self.insert_image_action)
    
    def _on_font_family_changed(self, family):
        """Handle font family change"""
        if family == "Default":
            family = "Segoe UI"
        
        format = QTextCharFormat()
        format.setFontFamily(family)
        self._merge_format(format)
    
    def _on_font_size_changed(self, size):
        """Handle font size change"""
        format = QTextCharFormat()
        format.setFontPointSize(float(size))
        self._merge_format(format)
    
    def _on_bold_triggered(self, checked):
        """Handle bold action"""
        format = QTextCharFormat()
        format.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        self._merge_format(format)
    
    def _on_italic_triggered(self, checked):
        """Handle italic action"""
        format = QTextCharFormat()
        format.setFontItalic(checked)
        self._merge_format(format)
    
    def _on_underline_triggered(self, checked):
        """Handle underline action"""
        format = QTextCharFormat()
        format.setFontUnderline(checked)
        self._merge_format(format)
    
    def _on_alignment_triggered(self, alignment):
        """Handle alignment actions"""
        self.editor.setAlignment(alignment)
    
    def _on_insert_image(self):
        """Handle insert image action"""
        # TODO: Implement image insertion
        print("Insert image clicked")
    
    def _merge_format(self, format):
        """Apply the given format to the selected text"""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(format)
        self.editor.mergeCurrentCharFormat(format)
    
    def _on_text_changed(self):
        """Handle text changes"""
        # TODO: Implement auto-save or other features
        pass
    
    def _add_sample_content(self):
        """Add sample content to the editor (for development only)"""
        sample_html = """
        <h1>Welcome to YT-Article Craft</h1>
        <p>This is a sample article demonstrating the rich text editing capabilities of the editor pane.</p>
        <p>You can format text with <b>bold</b>, <i>italic</i>, and <u>underline</u> styles.</p>
        <p>You can also create lists:</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <p>And add images and other media elements.</p>
        <h2>Getting Started</h2>
        <p>To create a new article, simply enter a YouTube URL and click "Generate Article".</p>
        """
        self.editor.setHtml(sample_html) 