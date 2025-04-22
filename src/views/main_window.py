"""
Main window class for YT-Article Craft
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, QSplitter, 
    QVBoxLayout, QHBoxLayout, QMenuBar, QStatusBar, 
    QMenu, QToolBar, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon

from app.config import Config
from app.constants import UI_MAIN_TITLE, DEFAULT_STYLE_SHEET
from views.task_dock import TaskDock
from views.editor_pane import EditorPane
from views.preview_pane import PreviewPane
from views.dialogs.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    """Main application window with three panel layout"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        # Load configuration
        self.config = Config()
        
        # Set window properties
        self.setWindowTitle(UI_MAIN_TITLE)
        self.resize(
            self.config.get("ui", "window_width", 1280),
            self.config.get("ui", "window_height", 800)
        )
        
        # Set minimum window size
        self.setMinimumSize(800, 600)
        
        # Set stylesheet
        self.setStyleSheet(DEFAULT_STYLE_SHEET)
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface"""
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout with splitter
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        # Create the three main panels
        self._setup_task_dock()
        self._setup_editor_pane()
        self._setup_preview_pane()
        
        # Set initial splitter sizes from config
        splitter_sizes = self.config.get("ui", "splitter_sizes", [250, 680, 350])
        self.main_splitter.setSizes(splitter_sizes)
        
        # Setup menu and status bar
        self._setup_menu_bar()
        self._setup_status_bar()
        
    def _setup_task_dock(self):
        """Setup the task dock panel (left panel)"""
        # Create task dock widget
        self.task_dock_widget = QDockWidget("Tasks", self)
        self.task_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable | 
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.task_dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # Set minimum and maximum width
        min_width = self.config.get("ui", "task_dock_min_width", 200)
        max_width = self.config.get("ui", "task_dock_max_width", 400)
        self.task_dock_widget.setMinimumWidth(min_width)
        self.task_dock_widget.setMaximumWidth(max_width)
        
        # Create task dock content
        self.task_dock = TaskDock()
        self.task_dock_widget.setWidget(self.task_dock)
        
        # Add to splitter
        self.main_splitter.addWidget(self.task_dock_widget)
        
    def _setup_editor_pane(self):
        """Setup the editor pane (middle panel)"""
        # Create editor pane
        self.editor_pane = EditorPane()
        
        # Set minimum width
        min_width = self.config.get("ui", "editor_pane_min_width", 400)
        self.editor_pane.setMinimumWidth(min_width)
        
        # Add to splitter
        self.main_splitter.addWidget(self.editor_pane)
        
    def _setup_preview_pane(self):
        """Setup the preview pane (right panel)"""
        # Create preview dock widget
        self.preview_dock_widget = QDockWidget("Preview", self)
        self.preview_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable | 
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.preview_dock_widget.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # Set minimum and maximum width
        min_width = self.config.get("ui", "preview_pane_min_width", 300)
        max_width = self.config.get("ui", "preview_pane_max_width", 600)
        self.preview_dock_widget.setMinimumWidth(min_width)
        self.preview_dock_widget.setMaximumWidth(max_width)
        
        # Create preview pane content
        self.preview_pane = PreviewPane()
        self.preview_dock_widget.setWidget(self.preview_pane)
        
        # Add to splitter
        self.main_splitter.addWidget(self.preview_dock_widget)
    
    def _setup_menu_bar(self):
        """Setup the menu bar"""
        self.menu_bar = self.menuBar()
        
        # File menu
        self.file_menu = self.menu_bar.addMenu("&File")
        
        # New task action
        self.new_task_action = QAction("&New Task", self)
        self.new_task_action.setShortcut("Ctrl+N")
        self.new_task_action.triggered.connect(self._on_new_task)
        self.file_menu.addAction(self.new_task_action)
        
        # Open task action
        self.open_task_action = QAction("&Open Task", self)
        self.open_task_action.setShortcut("Ctrl+O")
        self.open_task_action.triggered.connect(self._on_open_task)
        self.file_menu.addAction(self.open_task_action)
        
        self.file_menu.addSeparator()
        
        # Settings action
        self.settings_action = QAction("&Settings", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self._on_settings)
        self.file_menu.addAction(self.settings_action)
        
        self.file_menu.addSeparator()
        
        # Exit action
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("&Edit")
        
        # View menu
        self.view_menu = self.menu_bar.addMenu("&View")
        
        # Panel navigation shortcuts
        self.focus_task_dock_action = QAction("Focus &Tasks Panel", self)
        self.focus_task_dock_action.setShortcut("Ctrl+1")
        self.focus_task_dock_action.triggered.connect(
            lambda: self.task_dock.setFocus()
        )
        self.view_menu.addAction(self.focus_task_dock_action)
        
        self.focus_editor_action = QAction("Focus &Editor Panel", self)
        self.focus_editor_action.setShortcut("Ctrl+2")
        self.focus_editor_action.triggered.connect(
            lambda: self.editor_pane.setFocus()
        )
        self.view_menu.addAction(self.focus_editor_action)
        
        self.focus_preview_action = QAction("Focus &Preview Panel", self)
        self.focus_preview_action.setShortcut("Ctrl+3")
        self.focus_preview_action.triggered.connect(
            lambda: self.preview_pane.setFocus()
        )
        self.view_menu.addAction(self.focus_preview_action)
        
        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        
    def _setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _on_new_task(self):
        """Handle new task action"""
        # To be implemented
        self.status_bar.showMessage("New task created")
    
    def _on_open_task(self):
        """Handle open task action"""
        # To be implemented
        self.status_bar.showMessage("Task opened")
    
    def _on_settings(self):
        """Handle settings action"""
        settings_dialog = SettingsDialog(self, self.config)
        if settings_dialog.exec():
            # Update UI based on new settings
            self._apply_settings()
            self.status_bar.showMessage("Settings updated")
    
    def _apply_settings(self):
        """Apply settings from configuration"""
        # Update window size if needed
        
        # Update panel sizes
        task_dock_width = self.config.get("ui", "task_dock_width", 250)
        preview_pane_width = self.config.get("ui", "preview_pane_width", 350)
        
        # Calculate editor width based on window width minus task and preview widths
        window_width = self.width()
        editor_width = window_width - task_dock_width - preview_pane_width
        
        # Update splitter sizes
        self.main_splitter.setSizes([task_dock_width, editor_width, preview_pane_width])
        
        # Apply theme if necessary
        theme = self.config.get("app", "theme", "default")
        # In a full implementation, we would apply theme changes here
        
        # Update font - this would ideally happen at the application level
        # but for now we can update the parts we have access to
        font_family = self.config.get("ui", "font_family", "Segoe UI")
        font_size = self.config.get("ui", "font_size", 10)
        
        # Apply font to application (would require more complete implementation)
        # For now we just update what we can access
        
        # Update editor font
        editor_font_family = self.config.get("ui", "editor_font_family", "Consolas")
        editor_font_size = self.config.get("ui", "editor_font_size", 12)
        self.editor_pane.set_font(editor_font_family, editor_font_size)
        
        # Update auto-save settings
        auto_save = self.config.get("app", "auto_save", True)
        auto_save_interval = self.config.get("app", "auto_save_interval", 300)
        # Implementation of auto-save would be here
        
        # Update word count visibility in status bar if applicable
        show_word_count = self.config.get("editor", "show_word_count", True)
        # Implementation would update status bar configuration
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save splitter sizes to config
        self.config.set("ui", "splitter_sizes", self.main_splitter.sizes())
        
        # Save window size
        self.config.set("ui", "window_width", self.width())
        self.config.set("ui", "window_height", self.height())
        
        # Save settings
        self.config.save()
        
        # Accept the close event
        event.accept() 