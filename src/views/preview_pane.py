"""
Preview Pane for YT-Article Craft
Displays a preview of the article with Medium/WordPress styling
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QComboBox, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

class PreviewPane(QWidget):
    """Preview pane widget for previewing article content"""
    
    def __init__(self):
        """Initialize the preview pane"""
        super().__init__()
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
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
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # Create preview type selector
        self.preview_layout = QHBoxLayout()
        self.preview_label = QLabel("Preview as:")
        self.preview_type = QComboBox()
        self.preview_type.addItems(["Medium", "WordPress", "Plain HTML"])
        self.preview_type.currentTextChanged.connect(self._on_preview_type_changed)
        self.preview_layout.addWidget(self.preview_label)
        self.preview_layout.addWidget(self.preview_type)
        self.layout.addLayout(self.preview_layout)
        
        # Create web view for preview
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.layout.addWidget(self.web_view)
        
        # Create button bar
        self.button_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._on_refresh)
        self.button_layout.addWidget(self.refresh_button)
        
        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._on_export)
        self.button_layout.addWidget(self.export_button)
        
        # Publish button
        self.publish_button = QPushButton("Publish")
        self.publish_button.clicked.connect(self._on_publish)
        self.button_layout.addWidget(self.publish_button)
        
        self.layout.addLayout(self.button_layout)
    
    def _on_preview_type_changed(self, preview_type):
        """Handle preview type change"""
        # TODO: Implement different preview styles
        print(f"Preview type changed to {preview_type}")
        self._refresh_preview()
    
    def _on_refresh(self):
        """Handle refresh button click"""
        self._refresh_preview()
        print("Preview refreshed")
    
    def _on_export(self):
        """Handle export button click"""
        # TODO: Implement export functionality
        print("Export clicked")
    
    def _on_publish(self):
        """Handle publish button click"""
        # TODO: Implement publish functionality
        print("Publish clicked")
    
    def _refresh_preview(self):
        """Refresh the preview content"""
        # In a real application, this would get the content from the editor pane
        # For now, we'll just use the sample content
        preview_type = self.preview_type.currentText()
        
        if preview_type == "Medium":
            self._add_sample_content_medium()
        elif preview_type == "WordPress":
            self._add_sample_content_wordpress()
        else:
            self._add_sample_content()
    
    def _add_sample_content(self):
        """Add sample content to the preview (Plain HTML)"""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Article Preview</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 1em;
                }
                h1, h2, h3 {
                    color: #333;
                }
                h1 {
                    font-size: 2em;
                    margin-bottom: 0.5em;
                }
                h2 {
                    font-size: 1.5em;
                    margin-top: 1.5em;
                }
                p {
                    margin-bottom: 1em;
                }
                img {
                    max-width: 100%;
                    height: auto;
                    margin: 1em 0;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to YT-Article Craft</h1>
            <p>This is a sample article demonstrating the preview capabilities.</p>
            <p>You can see how your formatted text will appear in the final article.</p>
            <h2>Getting Started</h2>
            <p>To create a new article, simply enter a YouTube URL and click "Generate Article".</p>
            <p>The application will automatically:</p>
            <ul>
                <li>Download the video</li>
                <li>Generate a transcript</li>
                <li>Extract key points</li>
                <li>Create an article in your chosen style</li>
            </ul>
            <h2>Features</h2>
            <p>YT-Article Craft offers many powerful features:</p>
            <ul>
                <li>AI-powered content generation</li>
                <li>Medium-style formatting</li>
                <li>WordPress integration</li>
                <li>Export to various formats</li>
            </ul>
        </body>
        </html>
        """
        self.web_view.setHtml(sample_html)
    
    def _add_sample_content_medium(self):
        """Add sample content to the preview (Medium style)"""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Article Preview - Medium Style</title>
            <style>
                body {
                    font-family: 'Charter', 'Bitstream Charter', 'Sitka Text', Cambria, serif;
                    line-height: 1.7;
                    color: rgba(0, 0, 0, 0.84);
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 2em;
                    background-color: #fff;
                }
                h1, h2, h3 {
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    font-weight: 700;
                    line-height: 1.3;
                }
                h1 {
                    font-size: 2.5em;
                    margin-bottom: 0.3em;
                    letter-spacing: -0.02em;
                }
                h2 {
                    font-size: 1.6em;
                    margin-top: 2em;
                    margin-bottom: 0.5em;
                }
                p {
                    margin-bottom: 1.5em;
                    font-size: 1.2em;
                }
                blockquote {
                    border-left: 3px solid rgba(0, 0, 0, 0.84);
                    margin-left: -20px;
                    padding-left: 20px;
                    font-style: italic;
                    margin-bottom: 1.5em;
                }
                img {
                    max-width: 100%;
                    height: auto;
                    margin: 2em 0;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to YT-Article Craft</h1>
            <p>This is a sample article demonstrating the Medium-style preview capabilities. Notice the typography and spacing that mimics the Medium publishing platform.</p>
            
            <blockquote>YT-Article Craft helps you turn YouTube videos into beautiful, shareable articles with just a few clicks.</blockquote>
            
            <p>You can see how your formatted text will appear in the final article when published to Medium. The spacing, font choices, and overall aesthetic are designed to match Medium's clean and readable style.</p>
            
            <h2>Getting Started</h2>
            <p>To create a new article, simply enter a YouTube URL and click "Generate Article". The AI will handle the rest, transforming video content into well-structured written content.</p>
            
            <h2>Key Features</h2>
            <p>YT-Article Craft offers many powerful features tailored for content creators who want to repurpose video content:</p>
            <ul>
                <li>AI-powered content generation that maintains the original voice</li>
                <li>Automatic extraction of key points and quotes</li>
                <li>Medium-style formatting that looks professional</li>
                <li>One-click publishing to your Medium account</li>
                <li>SEO optimization to help your content reach more readers</li>
            </ul>
        </body>
        </html>
        """
        self.web_view.setHtml(sample_html)
    
    def _add_sample_content_wordpress(self):
        """Add sample content to the preview (WordPress style)"""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Article Preview - WordPress Style</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
                    line-height: 1.6;
                    color: #444;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 2em;
                    background-color: #f9f9f9;
                }
                .wordpress-container {
                    background-color: #fff;
                    padding: 2em;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                h1, h2, h3 {
                    color: #23282d;
                }
                h1 {
                    font-size: 2.2em;
                    margin-bottom: 0.5em;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 0.3em;
                }
                h2 {
                    font-size: 1.6em;
                    margin-top: 1.8em;
                    margin-bottom: 0.6em;
                }
                p {
                    margin-bottom: 1.2em;
                    font-size: 1.1em;
                }
                img {
                    max-width: 100%;
                    height: auto;
                    margin: 1.5em 0;
                }
                .wp-caption {
                    max-width: 100%;
                    background: #f9f9f9;
                    border: 1px solid #eee;
                    padding: 5px;
                    margin-bottom: 1.2em;
                    text-align: center;
                }
                .wp-caption-text {
                    font-size: 0.9em;
                    font-style: italic;
                    margin-top: 5px;
                }
            </style>
        </head>
        <body>
            <div class="wordpress-container">
                <h1>Welcome to YT-Article Craft</h1>
                <p>This is a sample article demonstrating the WordPress-style preview capabilities. Notice the typography and layout that mimics a typical WordPress blog post.</p>
                
                <div class="wp-caption">
                    <img src="https://via.placeholder.com/800x400" alt="Placeholder Image">
                    <p class="wp-caption-text">A sample image with caption in WordPress style</p>
                </div>
                
                <p>You can see how your formatted text will appear in the final article when published to WordPress. The spacing, font choices, and overall aesthetic are designed to match WordPress's default theme.</p>
                
                <h2>Getting Started</h2>
                <p>To create a new article, simply enter a YouTube URL and click "Generate Article". The application will automatically process the video and create a well-structured article.</p>
                
                <h2>Key Features</h2>
                <p>YT-Article Craft offers many powerful features tailored for WordPress bloggers:</p>
                <ul>
                    <li>AI-powered content generation</li>
                    <li>WordPress-optimized formatting</li>
                    <li>Featured image extraction</li>
                    <li>Direct WordPress integration</li>
                    <li>SEO metadata generation</li>
                </ul>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(sample_html) 