"""
Main window class for YT-Article Craft
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, QSplitter, 
    QVBoxLayout, QHBoxLayout, QMenuBar, QStatusBar, 
    QMenu, QToolBar, QApplication, QDialogButtonBox,
    QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut, QActionGroup

from app.config import Config
from app.constants import UI_MAIN_TITLE, DEFAULT_STYLE_SHEET
from views.task_dock import TaskDock
from views.editor_pane import EditorPane
from views.preview_pane import PreviewPane
from views.dialogs.settings_dialog import SettingsDialog
from views.dialogs.new_task_dialog import NewTaskDialog
from views.dialogs.template_dialog import TemplateDialog
from views.dialogs.about_dialog import AboutDialog

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
        
        # Setup toolbar
        self._setup_toolbar()
        
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
        self.new_task_action = QAction(QIcon(":/icons/new_task.png"), "&New Task", self)
        self.new_task_action.setShortcut("Ctrl+N")
        self.new_task_action.setStatusTip("Create a new task")
        self.new_task_action.triggered.connect(self._on_new_task)
        self.file_menu.addAction(self.new_task_action)
        
        # Open task action
        self.open_task_action = QAction(QIcon(":/icons/open_task.png"), "&Open Task", self)
        self.open_task_action.setShortcut("Ctrl+O")
        self.open_task_action.setStatusTip("Open an existing task")
        self.open_task_action.triggered.connect(self._on_open_task)
        self.file_menu.addAction(self.open_task_action)
        
        # Save task action
        self.save_task_action = QAction(QIcon(":/icons/save.png"), "&Save", self)
        self.save_task_action.setShortcut("Ctrl+S")
        self.save_task_action.setStatusTip("Save the current task")
        self.save_task_action.triggered.connect(self._on_save_task)
        self.file_menu.addAction(self.save_task_action)
        
        # Save as action
        self.save_as_action = QAction(QIcon(":/icons/save_as.png"), "Save &As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.setStatusTip("Save the current task with a new name")
        self.save_as_action.triggered.connect(self._on_save_as)
        self.file_menu.addAction(self.save_as_action)
        
        self.file_menu.addSeparator()
        
        # Export submenu
        self.export_menu = QMenu("&Export", self)
        self.export_menu.setIcon(QIcon(":/icons/export.png"))
        
        # Export as HTML
        self.export_html_action = QAction("Export as &HTML...", self)
        self.export_html_action.setStatusTip("Export the current article as HTML")
        self.export_html_action.triggered.connect(self._on_export_html)
        self.export_menu.addAction(self.export_html_action)
        
        # Export as Markdown
        self.export_md_action = QAction("Export as &Markdown...", self)
        self.export_md_action.setStatusTip("Export the current article as Markdown")
        self.export_md_action.triggered.connect(self._on_export_markdown)
        self.export_menu.addAction(self.export_md_action)
        
        # Export as PDF
        self.export_pdf_action = QAction("Export as &PDF...", self)
        self.export_pdf_action.setStatusTip("Export the current article as PDF")
        self.export_pdf_action.triggered.connect(self._on_export_pdf)
        self.export_menu.addAction(self.export_pdf_action)
        
        self.file_menu.addMenu(self.export_menu)
        
        # Publish submenu
        self.publish_menu = QMenu("&Publish", self)
        self.publish_menu.setIcon(QIcon(":/icons/publish.png"))
        
        # Publish to Medium
        self.publish_medium_action = QAction("Publish to &Medium...", self)
        self.publish_medium_action.setStatusTip("Publish the current article to Medium")
        self.publish_medium_action.triggered.connect(self._on_publish_medium)
        self.publish_menu.addAction(self.publish_medium_action)
        
        # Publish to WordPress
        self.publish_wp_action = QAction("Publish to &WordPress...", self)
        self.publish_wp_action.setStatusTip("Publish the current article to WordPress")
        self.publish_wp_action.triggered.connect(self._on_publish_wordpress)
        self.publish_menu.addAction(self.publish_wp_action)
        
        self.file_menu.addMenu(self.publish_menu)
        
        self.file_menu.addSeparator()
        
        # Settings action
        self.settings_action = QAction(QIcon(":/icons/settings.png"), "&Settings", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.setStatusTip("Edit application settings")
        self.settings_action.triggered.connect(self._on_settings)
        self.file_menu.addAction(self.settings_action)
        
        self.file_menu.addSeparator()
        
        # Exit action
        self.exit_action = QAction(QIcon(":/icons/exit.png"), "E&xit", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)
        
        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("&Edit")
        
        # Undo action
        self.undo_action = QAction(QIcon(":/icons/undo.png"), "&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setStatusTip("Undo the last action")
        self.undo_action.triggered.connect(self._on_undo)
        self.edit_menu.addAction(self.undo_action)
        
        # Redo action
        self.redo_action = QAction(QIcon(":/icons/redo.png"), "&Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setStatusTip("Redo the last undone action")
        self.redo_action.triggered.connect(self._on_redo)
        self.edit_menu.addAction(self.redo_action)
        
        self.edit_menu.addSeparator()
        
        # Cut action
        self.cut_action = QAction(QIcon(":/icons/cut.png"), "Cu&t", self)
        self.cut_action.setShortcut("Ctrl+X")
        self.cut_action.setStatusTip("Cut the selected text")
        self.cut_action.triggered.connect(self._on_cut)
        self.edit_menu.addAction(self.cut_action)
        
        # Copy action
        self.copy_action = QAction(QIcon(":/icons/copy.png"), "&Copy", self)
        self.copy_action.setShortcut("Ctrl+C")
        self.copy_action.setStatusTip("Copy the selected text")
        self.copy_action.triggered.connect(self._on_copy)
        self.edit_menu.addAction(self.copy_action)
        
        # Paste action
        self.paste_action = QAction(QIcon(":/icons/paste.png"), "&Paste", self)
        self.paste_action.setShortcut("Ctrl+V")
        self.paste_action.setStatusTip("Paste text from clipboard")
        self.paste_action.triggered.connect(self._on_paste)
        self.edit_menu.addAction(self.paste_action)
        
        self.edit_menu.addSeparator()
        
        # Select all action
        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_all_action.setStatusTip("Select all text")
        self.select_all_action.triggered.connect(self._on_select_all)
        self.edit_menu.addAction(self.select_all_action)
        
        self.edit_menu.addSeparator()
        
        # Find action
        self.find_action = QAction(QIcon(":/icons/find.png"), "&Find", self)
        self.find_action.setShortcut("Ctrl+F")
        self.find_action.setStatusTip("Find text in the document")
        self.find_action.triggered.connect(self._on_find)
        self.edit_menu.addAction(self.find_action)
        
        # Replace action
        self.replace_action = QAction("&Replace", self)
        self.replace_action.setShortcut("Ctrl+H")
        self.replace_action.setStatusTip("Replace text in the document")
        self.replace_action.triggered.connect(self._on_replace)
        self.edit_menu.addAction(self.replace_action)
        
        # Templates submenu
        self.templates_menu = QMenu("Te&mplates", self)
        self.templates_menu.setIcon(QIcon(":/icons/template.png"))
        
        # Manage templates action
        self.manage_templates_action = QAction("&Manage Templates...", self)
        self.manage_templates_action.setStatusTip("Manage article templates")
        self.manage_templates_action.triggered.connect(self._on_manage_templates)
        self.templates_menu.addAction(self.manage_templates_action)
        
        self.templates_menu.addSeparator()
        
        # New template action
        self.new_template_action = QAction("&New Template...", self)
        self.new_template_action.setStatusTip("Create a new article template")
        self.new_template_action.triggered.connect(self._on_new_template)
        self.templates_menu.addAction(self.new_template_action)
        
        self.edit_menu.addSeparator()
        self.edit_menu.addMenu(self.templates_menu)
        
        # View menu
        self.view_menu = self.menu_bar.addMenu("&View")
        
        # Toggle task panel action
        self.toggle_task_panel_action = QAction("&Task Panel", self)
        self.toggle_task_panel_action.setCheckable(True)
        self.toggle_task_panel_action.setChecked(True)
        self.toggle_task_panel_action.setStatusTip("Show or hide the task panel")
        self.toggle_task_panel_action.triggered.connect(self._on_toggle_task_panel)
        self.view_menu.addAction(self.toggle_task_panel_action)
        
        # Toggle preview panel action
        self.toggle_preview_panel_action = QAction("&Preview Panel", self)
        self.toggle_preview_panel_action.setCheckable(True)
        self.toggle_preview_panel_action.setChecked(True)
        self.toggle_preview_panel_action.setStatusTip("Show or hide the preview panel")
        self.toggle_preview_panel_action.triggered.connect(self._on_toggle_preview_panel)
        self.view_menu.addAction(self.toggle_preview_panel_action)
        
        # Toggle toolbar action
        self.toggle_toolbar_action = QAction("&Toolbar", self)
        self.toggle_toolbar_action.setCheckable(True)
        self.toggle_toolbar_action.setChecked(True)
        self.toggle_toolbar_action.setStatusTip("Show or hide the toolbar")
        self.toggle_toolbar_action.triggered.connect(self._on_toggle_toolbar)
        self.view_menu.addAction(self.toggle_toolbar_action)
        
        # Toggle status bar action
        self.toggle_statusbar_action = QAction("&Status Bar", self)
        self.toggle_statusbar_action.setCheckable(True)
        self.toggle_statusbar_action.setChecked(True)
        self.toggle_statusbar_action.setStatusTip("Show or hide the status bar")
        self.toggle_statusbar_action.triggered.connect(self._on_toggle_statusbar)
        self.view_menu.addAction(self.toggle_statusbar_action)
        
        self.view_menu.addSeparator()
        
        # Preview mode submenu
        self.preview_mode_menu = QMenu("Preview &Mode", self)
        
        # Medium preview mode
        self.medium_preview_action = QAction("&Medium", self)
        self.medium_preview_action.setCheckable(True)
        self.medium_preview_action.setChecked(True)
        self.medium_preview_action.setStatusTip("Preview article in Medium style")
        self.medium_preview_action.triggered.connect(
            lambda: self._on_change_preview_mode("medium")
        )
        self.preview_mode_menu.addAction(self.medium_preview_action)
        
        # WordPress preview mode
        self.wp_preview_action = QAction("&WordPress", self)
        self.wp_preview_action.setCheckable(True)
        self.wp_preview_action.setStatusTip("Preview article in WordPress style")
        self.wp_preview_action.triggered.connect(
            lambda: self._on_change_preview_mode("wordpress")
        )
        self.preview_mode_menu.addAction(self.wp_preview_action)
        
        # Plain preview mode
        self.plain_preview_action = QAction("&Plain", self)
        self.plain_preview_action.setCheckable(True)
        self.plain_preview_action.setStatusTip("Preview article in plain style")
        self.plain_preview_action.triggered.connect(
            lambda: self._on_change_preview_mode("plain")
        )
        self.preview_mode_menu.addAction(self.plain_preview_action)
        
        # Create a preview mode action group
        self.preview_mode_group = QActionGroup(self)
        self.preview_mode_group.addAction(self.medium_preview_action)
        self.preview_mode_group.addAction(self.wp_preview_action)
        self.preview_mode_group.addAction(self.plain_preview_action)
        self.preview_mode_group.setExclusive(True)
        
        self.view_menu.addMenu(self.preview_mode_menu)
        
        self.view_menu.addSeparator()
        
        # Panel navigation shortcuts
        self.focus_task_dock_action = QAction("Focus &Tasks Panel", self)
        self.focus_task_dock_action.setShortcut("Ctrl+1")
        self.focus_task_dock_action.setStatusTip("Switch focus to tasks panel")
        self.focus_task_dock_action.triggered.connect(
            lambda: self.task_dock.setFocus()
        )
        self.view_menu.addAction(self.focus_task_dock_action)
        
        self.focus_editor_action = QAction("Focus &Editor Panel", self)
        self.focus_editor_action.setShortcut("Ctrl+2")
        self.focus_editor_action.setStatusTip("Switch focus to editor panel")
        self.focus_editor_action.triggered.connect(
            lambda: self.editor_pane.setFocus()
        )
        self.view_menu.addAction(self.focus_editor_action)
        
        self.focus_preview_action = QAction("Focus &Preview Panel", self)
        self.focus_preview_action.setShortcut("Ctrl+3")
        self.focus_preview_action.setStatusTip("Switch focus to preview panel")
        self.focus_preview_action.triggered.connect(
            lambda: self.preview_pane.setFocus()
        )
        self.view_menu.addAction(self.focus_preview_action)
        
        # Task menu
        self.task_menu = self.menu_bar.addMenu("&Task")
        
        # Create task action
        self.create_task_action = QAction(QIcon(":/icons/new_task.png"), "&New Task", self)
        self.create_task_action.setStatusTip("Create a new task")
        self.create_task_action.triggered.connect(self._on_new_task)
        self.task_menu.addAction(self.create_task_action)
        
        # Edit task action
        self.edit_task_action = QAction(QIcon(":/icons/edit_task.png"), "&Edit Task", self)
        self.edit_task_action.setStatusTip("Edit the current task")
        self.edit_task_action.triggered.connect(self._on_edit_task)
        self.task_menu.addAction(self.edit_task_action)
        
        # Delete task action
        self.delete_task_action = QAction(QIcon(":/icons/delete_task.png"), "&Delete Task", self)
        self.delete_task_action.setStatusTip("Delete the current task")
        self.delete_task_action.triggered.connect(self._on_delete_task)
        self.task_menu.addAction(self.delete_task_action)
        
        self.task_menu.addSeparator()
        
        # Process video action
        self.process_video_action = QAction(QIcon(":/icons/process.png"), "&Process Video", self)
        self.process_video_action.setStatusTip("Start processing the video for the current task")
        self.process_video_action.triggered.connect(self._on_process_video)
        self.task_menu.addAction(self.process_video_action)
        
        # Generate article action
        self.generate_article_action = QAction(QIcon(":/icons/generate.png"), "&Generate Article", self)
        self.generate_article_action.setStatusTip("Generate an article from the processed video")
        self.generate_article_action.triggered.connect(self._on_generate_article)
        self.task_menu.addAction(self.generate_article_action)
        
        # Help menu
        self.help_menu = self.menu_bar.addMenu("&Help")
        
        # Help contents action
        self.help_contents_action = QAction(QIcon(":/icons/help.png"), "&Help Contents", self)
        self.help_contents_action.setShortcut("F1")
        self.help_contents_action.setStatusTip("View help contents")
        self.help_contents_action.triggered.connect(self._on_help_contents)
        self.help_menu.addAction(self.help_contents_action)
        
        # Check for updates action
        self.check_updates_action = QAction("&Check for Updates", self)
        self.check_updates_action.setStatusTip("Check for application updates")
        self.check_updates_action.triggered.connect(self._on_check_updates)
        self.help_menu.addAction(self.check_updates_action)
        
        self.help_menu.addSeparator()
        
        # About action
        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("Show information about the application")
        self.about_action.triggered.connect(self._on_about)
        self.help_menu.addAction(self.about_action)
        
    def _setup_toolbar(self):
        """Setup the toolbar"""
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setIconSize(QSize(24, 24))
        self.main_toolbar.setMovable(False)
        self.addToolBar(self.main_toolbar)
        
        # Add actions to toolbar
        self.main_toolbar.addAction(self.new_task_action)
        self.main_toolbar.addAction(self.open_task_action)
        self.main_toolbar.addAction(self.save_task_action)
        
        self.main_toolbar.addSeparator()
        
        self.main_toolbar.addAction(self.undo_action)
        self.main_toolbar.addAction(self.redo_action)
        
        self.main_toolbar.addSeparator()
        
        self.main_toolbar.addAction(self.cut_action)
        self.main_toolbar.addAction(self.copy_action)
        self.main_toolbar.addAction(self.paste_action)
        
        self.main_toolbar.addSeparator()
        
        self.main_toolbar.addAction(self.process_video_action)
        self.main_toolbar.addAction(self.generate_article_action)
        
        # Set toolbar visibility from config
        toolbar_visible = self.config.get("ui", "toolbar_visible", True)
        self.main_toolbar.setVisible(toolbar_visible)
        self.toggle_toolbar_action.setChecked(toolbar_visible)
    
    def _setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets to right side of status bar
        self.word_count_label = QLabel("Words: 0")
        self.status_bar.addPermanentWidget(self.word_count_label)
        
        self.char_count_label = QLabel("Characters: 0")
        self.status_bar.addPermanentWidget(self.char_count_label)
        
        # Set initial status message
        self.status_bar.showMessage("Ready")
        
        # Set status bar visibility from config
        status_bar_visible = self.config.get("ui", "status_bar_visible", True)
        self.status_bar.setVisible(status_bar_visible)
        self.toggle_statusbar_action.setChecked(status_bar_visible)
    
    # File menu handlers
    def _on_new_task(self):
        """Handle new task action"""
        dialog = NewTaskDialog(self)
        if dialog.exec():
            # Create new task with data from dialog
            task_data = dialog.get_task_data()
            # To be implemented: create and save task
            self.status_bar.showMessage("New task created")
    
    def _on_open_task(self):
        """Handle open task action"""
        # To be implemented: show task selection dialog
        self.status_bar.showMessage("Task opened")
    
    def _on_save_task(self):
        """Handle save task action"""
        # To be implemented: save current task
        self.status_bar.showMessage("Task saved")
    
    def _on_save_as(self):
        """Handle save as action"""
        # To be implemented: save current task with new name
        self.status_bar.showMessage("Task saved as new file")
    
    def _on_export_html(self):
        """Handle export as HTML action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as HTML", "", "HTML Files (*.html);;All Files (*)"
        )
        if file_path:
            # To be implemented: export as HTML
            self.status_bar.showMessage(f"Exported as HTML: {file_path}")
    
    def _on_export_markdown(self):
        """Handle export as Markdown action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as Markdown", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            # To be implemented: export as Markdown
            self.status_bar.showMessage(f"Exported as Markdown: {file_path}")
    
    def _on_export_pdf(self):
        """Handle export as PDF action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            # To be implemented: export as PDF
            self.status_bar.showMessage(f"Exported as PDF: {file_path}")
    
    def _on_publish_medium(self):
        """Handle publish to Medium action"""
        # To be implemented: publish to Medium
        self.status_bar.showMessage("Published to Medium")
    
    def _on_publish_wordpress(self):
        """Handle publish to WordPress action"""
        # To be implemented: publish to WordPress
        self.status_bar.showMessage("Published to WordPress")
    
    def _on_settings(self):
        """Handle settings action"""
        settings_dialog = SettingsDialog(self, self.config)
        if settings_dialog.exec():
            # Update UI based on new settings
            self._apply_settings()
            self.status_bar.showMessage("Settings updated")
    
    # Edit menu handlers
    def _on_undo(self):
        """Handle undo action"""
        if self.editor_pane.hasFocus():
            self.editor_pane.undo()
            self.status_bar.showMessage("Undone")
    
    def _on_redo(self):
        """Handle redo action"""
        if self.editor_pane.hasFocus():
            self.editor_pane.redo()
            self.status_bar.showMessage("Redone")
    
    def _on_cut(self):
        """Handle cut action"""
        focused_widget = QApplication.focusWidget()
        if hasattr(focused_widget, "cut"):
            focused_widget.cut()
            self.status_bar.showMessage("Cut to clipboard")
    
    def _on_copy(self):
        """Handle copy action"""
        focused_widget = QApplication.focusWidget()
        if hasattr(focused_widget, "copy"):
            focused_widget.copy()
            self.status_bar.showMessage("Copied to clipboard")
    
    def _on_paste(self):
        """Handle paste action"""
        focused_widget = QApplication.focusWidget()
        if hasattr(focused_widget, "paste"):
            focused_widget.paste()
            self.status_bar.showMessage("Pasted from clipboard")
    
    def _on_select_all(self):
        """Handle select all action"""
        focused_widget = QApplication.focusWidget()
        if hasattr(focused_widget, "selectAll"):
            focused_widget.selectAll()
            self.status_bar.showMessage("All text selected")
    
    def _on_find(self):
        """Handle find action"""
        # To be implemented: show find dialog
        self.status_bar.showMessage("Find dialog opened")
    
    def _on_replace(self):
        """Handle replace action"""
        # To be implemented: show replace dialog
        self.status_bar.showMessage("Replace dialog opened")
    
    def _on_manage_templates(self):
        """Handle manage templates action"""
        # To be implemented: show templates dialog
        self.status_bar.showMessage("Template management opened")
    
    def _on_new_template(self):
        """Handle new template action"""
        dialog = TemplateDialog(self)
        if dialog.exec():
            # Create new template with data from dialog
            template_data = dialog.get_template_data()
            # To be implemented: create and save template
            self.status_bar.showMessage("New template created")
    
    # View menu handlers
    def _on_toggle_task_panel(self, checked):
        """Handle toggle task panel action"""
        self.task_dock_widget.setVisible(checked)
        self.status_bar.showMessage(f"Task panel {'shown' if checked else 'hidden'}")
    
    def _on_toggle_preview_panel(self, checked):
        """Handle toggle preview panel action"""
        self.preview_dock_widget.setVisible(checked)
        self.status_bar.showMessage(f"Preview panel {'shown' if checked else 'hidden'}")
    
    def _on_toggle_toolbar(self, checked):
        """Handle toggle toolbar action"""
        self.main_toolbar.setVisible(checked)
        self.config.set("ui", "toolbar_visible", checked)
        self.status_bar.showMessage(f"Toolbar {'shown' if checked else 'hidden'}")
    
    def _on_toggle_statusbar(self, checked):
        """Handle toggle status bar action"""
        self.status_bar.setVisible(checked)
        self.config.set("ui", "status_bar_visible", checked)
        # Can't use status bar to show message when it's hidden
    
    def _on_change_preview_mode(self, mode):
        """Handle change preview mode action"""
        # To be implemented: change preview mode
        self.status_bar.showMessage(f"Preview mode changed to {mode}")
    
    # Task menu handlers
    def _on_edit_task(self):
        """Handle edit task action"""
        # To be implemented: edit current task
        self.status_bar.showMessage("Editing task")
    
    def _on_delete_task(self):
        """Handle delete task action"""
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this task?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # To be implemented: delete current task
            self.status_bar.showMessage("Task deleted")
    
    def _on_process_video(self):
        """Handle process video action"""
        # To be implemented: start video processing
        self.status_bar.showMessage("Processing video...")
    
    def _on_generate_article(self):
        """Handle generate article action"""
        # To be implemented: generate article
        self.status_bar.showMessage("Generating article...")
    
    # Help menu handlers
    def _on_help_contents(self):
        """Handle help contents action"""
        # To be implemented: show help documentation
        self.status_bar.showMessage("Help opened")
    
    def _on_check_updates(self):
        """Handle check for updates action"""
        # To be implemented: check for updates
        self.status_bar.showMessage("Checking for updates...")
    
    def _on_about(self):
        """Handle about action"""
        about_dialog = AboutDialog(self)
        about_dialog.exec()
    
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
        # Save window state
        self.config.set("ui", "window_width", self.width())
        self.config.set("ui", "window_height", self.height())
        self.config.set("ui", "splitter_sizes", self.main_splitter.sizes())
        
        # Save changes to config
        self.config.save()
        
        # Accept the close event
        event.accept() 