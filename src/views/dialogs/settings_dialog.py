"""
Settings dialog for the application
Allows configuring application preferences
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QWidget, QFormLayout, QLabel, QPushButton, 
                            QComboBox, QSpinBox, QCheckBox, QDialogButtonBox,
                            QFileDialog, QLineEdit, QGroupBox, QListWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase

class SettingsDialog(QDialog):
    """
    Dialog for configuring application settings
    """
    
    # Signal emitted when settings are applied
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None, config=None):
        """
        Initialize the settings dialog
        
        Args:
            parent: Parent widget
            config: Configuration object
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(550, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Store configuration
        self.config = config
        self.current_settings = self._get_settings_from_config() if config else {}
        
        # Initialize UI
        self._setup_ui()
        self._load_settings()
    
    def _get_settings_from_config(self):
        """Get settings from config object
        
        Returns:
            dict: Settings dictionary from config
        """
        settings = {
            # App settings
            "app_name": self.config.get("app", "name", "YT-Article Craft"),
            "theme": self.config.get("app", "theme", "default"),
            "language": self.config.get("app", "language", "en"),
            "save_path": self.config.get("app", "save_path", ""),
            "auto_save": self.config.get("app", "auto_save", True),
            "auto_save_interval": self.config.get("app", "auto_save_interval", 300) // 60,  # Convert to minutes
            
            # API settings
            "openai_api_key": self.config.get("api", "openai_api_key", ""),
            "medium_api_key": self.config.get("api", "medium_api_key", ""),
            "wordpress_api_key": self.config.get("api", "wordpress_api_key", ""),
            "deepl_api_key": self.config.get("api", "deepl_api_key", ""),
            "deepseek_api_key": self.config.get("api", "deepseek_api_key", ""),
            "deepseek_base_url": self.config.get("api", "deepseek_base_url", "https://api.deepseek.com/v1"),
            
            # UI settings
            "font_family": self.config.get("ui", "font_family", "Segoe UI"),
            "font_size": self.config.get("ui", "font_size", 10),
            "editor_font_family": self.config.get("ui", "editor_font_family", "Consolas"),
            "editor_font_size": self.config.get("ui", "editor_font_size", 12),
            "task_dock_width": self.config.get("ui", "task_dock_width", 250),
            "preview_pane_width": self.config.get("ui", "preview_pane_width", 350),
            
            # Additional settings not in config yet
            "spell_check": self.config.get("editor", "spell_check", True),
            "show_word_count": self.config.get("editor", "show_word_count", True),
            "restore_session": self.config.get("app", "restore_session", True),
            "show_notifications": self.config.get("app", "show_notifications", True),
            "confirm_exit": self.config.get("app", "confirm_exit", True)
        }
        return settings
    
    def _setup_ui(self):
        """Set up the dialog UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.appearance_tab = QWidget()
        self.editor_tab = QWidget()
        self.api_tab = QWidget()
        self.templates_tab = QWidget()
        
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.appearance_tab, "Appearance")
        self.tabs.addTab(self.editor_tab, "Editor")
        self.tabs.addTab(self.api_tab, "API Keys")
        self.tabs.addTab(self.templates_tab, "Templates")
        
        # Setup each tab
        self._setup_general_tab()
        self._setup_appearance_tab()
        self._setup_editor_tab()
        self._setup_api_tab()
        self._setup_templates_tab()
        
        # Button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply | 
            QDialogButtonBox.StandardButton.Reset
        )
        
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        self.button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self._reset_settings)
        
        # Add widgets to main layout
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.button_box)
    
    def _setup_general_tab(self):
        """Set up the general settings tab"""
        layout = QFormLayout(self.general_tab)
        
        # Application name
        self.app_name_edit = QLineEdit()
        layout.addRow("Application Name:", self.app_name_edit)
        
        # Language setting
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "中文", "Español", "Français", "Deutsch"])
        layout.addRow("Language:", self.language_combo)
        
        # Save path
        save_path_layout = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_save_path)
        save_path_layout.addWidget(self.save_path_edit)
        save_path_layout.addWidget(self.browse_button)
        layout.addRow("Save Path:", save_path_layout)
        
        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        
        # Auto-save
        self.auto_save_check = QCheckBox("Enable auto-save")
        behavior_layout.addWidget(self.auto_save_check)
        
        # Auto-save interval
        auto_save_interval_layout = QHBoxLayout()
        auto_save_interval_layout.addWidget(QLabel("Auto-save interval:"))
        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(1, 60)
        self.auto_save_interval_spin.setSuffix(" minutes")
        auto_save_interval_layout.addWidget(self.auto_save_interval_spin)
        auto_save_interval_layout.addStretch()
        behavior_layout.addLayout(auto_save_interval_layout)
        
        # Startup behavior
        self.restore_session_check = QCheckBox("Restore previous session on startup")
        behavior_layout.addWidget(self.restore_session_check)
        
        # Notifications
        self.show_notifications_check = QCheckBox("Show desktop notifications")
        behavior_layout.addWidget(self.show_notifications_check)
        
        # Confirm on exit
        self.confirm_exit_check = QCheckBox("Confirm before exiting with unsaved changes")
        behavior_layout.addWidget(self.confirm_exit_check)
        
        layout.addRow("", behavior_group)
    
    def _setup_appearance_tab(self):
        """Set up the appearance settings tab"""
        layout = QFormLayout(self.appearance_tab)
        
        # Theme setting
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        layout.addRow("Theme:", self.theme_combo)
        
        # Application font settings
        app_font_group = QGroupBox("Application Font")
        app_font_layout = QFormLayout(app_font_group)
        
        # Font family
        self.font_family_combo = QComboBox()
        # Get system fonts
        font_families = QFontDatabase.families()
        self.font_family_combo.addItems(font_families)
        app_font_layout.addRow("Font Family:", self.font_family_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        app_font_layout.addRow("Font Size:", self.font_size_spin)
        
        layout.addRow("", app_font_group)
        
        # Panel sizes
        panel_group = QGroupBox("Panel Sizes")
        panel_layout = QFormLayout(panel_group)
        
        # Task dock width
        self.task_dock_width_spin = QSpinBox()
        self.task_dock_width_spin.setRange(100, 500)
        self.task_dock_width_spin.setSuffix(" px")
        panel_layout.addRow("Task Dock Width:", self.task_dock_width_spin)
        
        # Preview pane width
        self.preview_pane_width_spin = QSpinBox()
        self.preview_pane_width_spin.setRange(200, 800)
        self.preview_pane_width_spin.setSuffix(" px")
        panel_layout.addRow("Preview Pane Width:", self.preview_pane_width_spin)
        
        layout.addRow("", panel_group)
    
    def _setup_editor_tab(self):
        """Set up the editor settings tab"""
        layout = QFormLayout(self.editor_tab)
        
        # Editor font settings
        editor_font_group = QGroupBox("Editor Font")
        editor_font_layout = QFormLayout(editor_font_group)
        
        # Editor font family
        self.editor_font_family_combo = QComboBox()
        # Get monospace fonts
        monospace_fonts = []
        for family in QFontDatabase.families():
            font = QFont(family)
            if font.fixedPitch():
                monospace_fonts.append(family)
        self.editor_font_family_combo.addItems(monospace_fonts)
        editor_font_layout.addRow("Font Family:", self.editor_font_family_combo)
        
        # Editor font size
        self.editor_font_size_spin = QSpinBox()
        self.editor_font_size_spin.setRange(8, 36)
        editor_font_layout.addRow("Font Size:", self.editor_font_size_spin)
        
        layout.addRow("", editor_font_group)
        
        # Editor features
        editor_features_group = QGroupBox("Editor Features")
        editor_features_layout = QVBoxLayout(editor_features_group)
        
        # Spell check
        self.spell_check_check = QCheckBox("Enable spell checking")
        editor_features_layout.addWidget(self.spell_check_check)
        
        # Word count
        self.show_word_count_check = QCheckBox("Show word count in status bar")
        editor_features_layout.addWidget(self.show_word_count_check)
        
        layout.addRow("", editor_features_group)
    
    def _setup_api_tab(self):
        """Set up the API settings tab"""
        layout = QFormLayout(self.api_tab)
        
        # OpenAI API key
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("OpenAI API Key:", self.openai_api_key_edit)
        
        # Medium API key
        self.medium_api_key_edit = QLineEdit()
        self.medium_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Medium API Key:", self.medium_api_key_edit)
        
        # WordPress API key
        self.wordpress_api_key_edit = QLineEdit()
        self.wordpress_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("WordPress API Key:", self.wordpress_api_key_edit)
        
        # DeepL API key
        self.deepl_api_key_edit = QLineEdit()
        self.deepl_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("DeepL API Key:", self.deepl_api_key_edit)
        
        # DeepSeek API key
        self.deepseek_api_key_edit = QLineEdit()
        self.deepseek_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("DeepSeek API Key:", self.deepseek_api_key_edit)
        
        # DeepSeek Base URL
        self.deepseek_base_url_edit = QLineEdit()
        layout.addRow("DeepSeek Base URL:", self.deepseek_base_url_edit)
    
    def _setup_templates_tab(self):
        """Set up the templates management tab"""
        layout = QVBoxLayout(self.templates_tab)
        
        # Templates list
        templates_group = QGroupBox("Saved Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.templates_list.currentItemChanged.connect(self._on_template_selected)
        templates_layout.addWidget(self.templates_list)
        
        # Template actions buttons
        buttons_layout = QHBoxLayout()
        self.new_template_btn = QPushButton("New")
        self.edit_template_btn = QPushButton("Edit")
        self.clone_template_btn = QPushButton("Clone")
        self.delete_template_btn = QPushButton("Delete")
        
        self.new_template_btn.clicked.connect(self._on_new_template)
        self.edit_template_btn.clicked.connect(self._on_edit_template)
        self.clone_template_btn.clicked.connect(self._on_clone_template)
        self.delete_template_btn.clicked.connect(self._on_delete_template)
        
        buttons_layout.addWidget(self.new_template_btn)
        buttons_layout.addWidget(self.edit_template_btn)
        buttons_layout.addWidget(self.clone_template_btn)
        buttons_layout.addWidget(self.delete_template_btn)
        buttons_layout.addStretch()
        templates_layout.addLayout(buttons_layout)
        
        # Template details group
        details_group = QGroupBox("Template Details")
        details_layout = QFormLayout(details_group)
        
        self.template_name_label = QLabel("")
        self.template_tone_label = QLabel("")
        self.template_brand_label = QLabel("")
        self.template_cta_label = QLabel("")
        
        details_layout.addRow("Name:", self.template_name_label)
        details_layout.addRow("Tone:", self.template_tone_label)
        details_layout.addRow("Brand Voice:", self.template_brand_label)
        details_layout.addRow("Call to Action:", self.template_cta_label)
        
        # Layout
        layout.addWidget(templates_group)
        layout.addWidget(details_group)
        
        # Initially disable buttons that need selection
        self.edit_template_btn.setEnabled(False)
        self.clone_template_btn.setEnabled(False)
        self.delete_template_btn.setEnabled(False)
    
    def _on_template_selected(self, current, previous):
        """Handle template selection in list"""
        has_selection = current is not None
        self.edit_template_btn.setEnabled(has_selection)
        self.clone_template_btn.setEnabled(has_selection)
        self.delete_template_btn.setEnabled(has_selection)
        
        if has_selection:
            # In a real implementation, this would load from the template database
            # using the item's data. For now, just update labels with placeholder data
            self.template_name_label.setText(current.text())
            self.template_tone_label.setText("Professional")
            self.template_brand_label.setText("Sample brand voice")
            self.template_cta_label.setText("Follow for more content")
        else:
            self.template_name_label.setText("")
            self.template_tone_label.setText("")
            self.template_brand_label.setText("")
            self.template_cta_label.setText("")
    
    def _on_new_template(self):
        """Create a new template"""
        # Placeholder - would open a template editor dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Create Template", 
                               "Template editor would open here.")
    
    def _on_edit_template(self):
        """Edit the selected template"""
        if not self.templates_list.currentItem():
            return
        
        # Placeholder - would open a template editor dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Edit Template", 
                               f"Editing template: {self.templates_list.currentItem().text()}")
    
    def _on_clone_template(self):
        """Clone the selected template"""
        if not self.templates_list.currentItem():
            return
        
        # Placeholder - would clone then open editor
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Clone Template", 
                               f"Cloning template: {self.templates_list.currentItem().text()}")
    
    def _on_delete_template(self):
        """Delete the selected template"""
        if not self.templates_list.currentItem():
            return
        
        # Placeholder - would confirm then delete
        from PyQt6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Delete Template", 
                              f"Are you sure you want to delete '{self.templates_list.currentItem().text()}'?",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.templates_list.takeItem(self.templates_list.currentRow())
    
    def _browse_save_path(self):
        """Browse for save path"""
        current_path = self.save_path_edit.text() or str(self.config.get("app", "save_path", ""))
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory", current_path)
        if directory:
            self.save_path_edit.setText(directory)
    
    def _load_settings(self):
        """Load current settings into UI components"""
        if not self.current_settings:
            return
        
        # General settings
        self.app_name_edit.setText(self.current_settings.get("app_name", "YT-Article Craft"))
        
        # Map language code to index
        language_map = {"en": 0, "zh": 1, "es": 2, "fr": 3, "de": 4}
        language_code = self.current_settings.get("language", "en")
        self.language_combo.setCurrentIndex(language_map.get(language_code, 0))
        
        self.save_path_edit.setText(self.current_settings.get("save_path", ""))
        self.auto_save_check.setChecked(self.current_settings.get("auto_save", True))
        self.auto_save_interval_spin.setValue(self.current_settings.get("auto_save_interval", 5))
        self.restore_session_check.setChecked(self.current_settings.get("restore_session", True))
        self.show_notifications_check.setChecked(self.current_settings.get("show_notifications", True))
        self.confirm_exit_check.setChecked(self.current_settings.get("confirm_exit", True))
        
        # Appearance settings
        theme_map = {"light": "Light", "dark": "Dark", "default": "System"}
        self.theme_combo.setCurrentText(theme_map.get(self.current_settings.get("theme", "default"), "System"))
        
        # Find system font in combo box
        font_family = self.current_settings.get("font_family", "Segoe UI")
        index = self.font_family_combo.findText(font_family, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.font_family_combo.setCurrentIndex(index)
        
        self.font_size_spin.setValue(self.current_settings.get("font_size", 10))
        self.task_dock_width_spin.setValue(self.current_settings.get("task_dock_width", 250))
        self.preview_pane_width_spin.setValue(self.current_settings.get("preview_pane_width", 350))
        
        # Editor settings
        editor_font_family = self.current_settings.get("editor_font_family", "Consolas")
        index = self.editor_font_family_combo.findText(editor_font_family, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.editor_font_family_combo.setCurrentIndex(index)
        
        self.editor_font_size_spin.setValue(self.current_settings.get("editor_font_size", 12))
        self.spell_check_check.setChecked(self.current_settings.get("spell_check", True))
        self.show_word_count_check.setChecked(self.current_settings.get("show_word_count", True))
        
        # API settings
        self.openai_api_key_edit.setText(self.current_settings.get("openai_api_key", ""))
        self.medium_api_key_edit.setText(self.current_settings.get("medium_api_key", ""))
        self.wordpress_api_key_edit.setText(self.current_settings.get("wordpress_api_key", ""))
        self.deepl_api_key_edit.setText(self.current_settings.get("deepl_api_key", ""))
        self.deepseek_api_key_edit.setText(self.current_settings.get("deepseek_api_key", ""))
        self.deepseek_base_url_edit.setText(self.current_settings.get("deepseek_base_url", "https://api.deepseek.com/v1"))
        
        # Load template list - in a real implementation, this would come from the database
        self.templates_list.clear()
        default_templates = ["Professional", "Casual", "Storytelling", "Technical", "Educational"]
        for template_name in default_templates:
            self.templates_list.addItem(template_name)
    
    def get_settings(self):
        """
        Get current settings from dialog
        
        Returns:
            dict: Settings dictionary
        """
        # Map language index to code
        language_codes = ["en", "zh", "es", "fr", "de"]
        language_index = self.language_combo.currentIndex()
        language_code = language_codes[language_index] if 0 <= language_index < len(language_codes) else "en"
        
        # Map theme text to value
        theme_map = {"Light": "light", "Dark": "dark", "System": "default"}
        theme = theme_map.get(self.theme_combo.currentText(), "default")
        
        settings = {
            # App settings
            "app_name": self.app_name_edit.text(),
            "theme": theme,
            "language": language_code,
            "save_path": self.save_path_edit.text(),
            "auto_save": self.auto_save_check.isChecked(),
            "auto_save_interval": self.auto_save_interval_spin.value() * 60,  # Convert to seconds
            "restore_session": self.restore_session_check.isChecked(),
            "show_notifications": self.show_notifications_check.isChecked(),
            "confirm_exit": self.confirm_exit_check.isChecked(),
            
            # UI settings
            "font_family": self.font_family_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "editor_font_family": self.editor_font_family_combo.currentText(),
            "editor_font_size": self.editor_font_size_spin.value(),
            "task_dock_width": self.task_dock_width_spin.value(),
            "preview_pane_width": self.preview_pane_width_spin.value(),
            
            # Editor settings
            "spell_check": self.spell_check_check.isChecked(),
            "show_word_count": self.show_word_count_check.isChecked(),
            
            # API settings
            "openai_api_key": self.openai_api_key_edit.text(),
            "medium_api_key": self.medium_api_key_edit.text(),
            "wordpress_api_key": self.wordpress_api_key_edit.text(),
            "deepl_api_key": self.deepl_api_key_edit.text(),
            "deepseek_api_key": self.deepseek_api_key_edit.text(),
            "deepseek_base_url": self.deepseek_base_url_edit.text()
        }
        
        return settings
    
    def _apply_settings(self):
        """Apply current settings"""
        settings = self.get_settings()
        if self.config:
            # Apply to config
            self._apply_to_config(settings)
            
        # Emit signal with settings
        self.settings_applied.emit(settings)
    
    def _apply_to_config(self, settings):
        """Apply settings to config object
        
        Args:
            settings (dict): Settings dictionary
        """
        # App settings
        self.config.set("app", "name", settings["app_name"])
        self.config.set("app", "theme", settings["theme"])
        self.config.set("app", "language", settings["language"])
        self.config.set("app", "save_path", settings["save_path"])
        self.config.set("app", "auto_save", settings["auto_save"])
        self.config.set("app", "auto_save_interval", settings["auto_save_interval"])
        self.config.set("app", "restore_session", settings["restore_session"])
        self.config.set("app", "show_notifications", settings["show_notifications"])
        self.config.set("app", "confirm_exit", settings["confirm_exit"])
        
        # UI settings
        self.config.set("ui", "font_family", settings["font_family"])
        self.config.set("ui", "font_size", settings["font_size"])
        self.config.set("ui", "editor_font_family", settings["editor_font_family"])
        self.config.set("ui", "editor_font_size", settings["editor_font_size"])
        self.config.set("ui", "task_dock_width", settings["task_dock_width"])
        self.config.set("ui", "preview_pane_width", settings["preview_pane_width"])
        
        # Editor settings
        self.config.set("editor", "spell_check", settings["spell_check"])
        self.config.set("editor", "show_word_count", settings["show_word_count"])
        
        # API settings
        self.config.set("api", "openai_api_key", settings["openai_api_key"])
        self.config.set("api", "medium_api_key", settings["medium_api_key"])
        self.config.set("api", "wordpress_api_key", settings["wordpress_api_key"])
        self.config.set("api", "deepl_api_key", settings["deepl_api_key"])
        self.config.set("api", "deepseek_api_key", settings["deepseek_api_key"])
        self.config.set("api", "deepseek_base_url", settings["deepseek_base_url"])
        
        # Save config
        self.config.save()
    
    def _reset_settings(self):
        """Reset settings to default values"""
        # Use config defaults if available
        if self.config:
            self.current_settings = self._get_settings_from_config()
        else:
            # Define default settings
            self.current_settings = {
                "app_name": "YT-Article Craft",
                "theme": "default",
                "language": "en",
                "save_path": "",
                "auto_save": True,
                "auto_save_interval": 5,
                "restore_session": True,
                "show_notifications": True,
                "confirm_exit": True,
                "font_family": "Segoe UI",
                "font_size": 10,
                "editor_font_family": "Consolas",
                "editor_font_size": 12,
                "task_dock_width": 250,
                "preview_pane_width": 350,
                "spell_check": True,
                "show_word_count": True,
                "openai_api_key": "",
                "medium_api_key": "",
                "wordpress_api_key": "",
                "deepl_api_key": "",
                "deepseek_api_key": "",
                "deepseek_base_url": "https://api.deepseek.com/v1"
            }
        
        # Reload settings into UI
        self._load_settings()
    
    def accept(self):
        """Dialog accepted"""
        self._apply_settings()
        super().accept() 