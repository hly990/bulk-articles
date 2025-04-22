"""
Task Dock panel for YT-Article Craft
Displays the list of tasks and provides controls for task management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListView, QLabel, QLineEdit, QToolBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon

class TaskDock(QWidget):
    """Task dock widget for displaying and managing tasks"""
    
    def __init__(self):
        """Initialize the task dock"""
        super().__init__()
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )
        
        # Initialize UI
        self._init_ui()
        
        # Populate with sample tasks (for development only)
        self._add_sample_tasks()
        
    def _init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # Create search box
        self.search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks...")
        self.search_layout.addWidget(self.search_input)
        self.layout.addLayout(self.search_layout)
        
        # Create task list
        self.task_list = QListView()
        self.task_model = QStandardItemModel()
        self.task_list.setModel(self.task_model)
        self.task_list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.task_list.clicked.connect(self._on_task_selected)
        self.layout.addWidget(self.task_list)
        
        # Create buttons bar
        self.button_layout = QHBoxLayout()
        
        # Add task button
        self.add_button = QPushButton("New Task")
        self.add_button.clicked.connect(self._on_add_task)
        self.button_layout.addWidget(self.add_button)
        
        # Remove task button
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._on_remove_task)
        self.button_layout.addWidget(self.remove_button)
        
        self.layout.addLayout(self.button_layout)
    
    def _add_sample_tasks(self):
        """Add sample tasks to the list (for development only)"""
        samples = [
            "Introduction to Python Programming",
            "Web Development with Django",
            "Machine Learning Basics",
            "Data Analysis with Pandas",
            "PyQt6 GUI Development"
        ]
        
        for sample in samples:
            item = QStandardItem(sample)
            self.task_model.appendRow(item)
    
    def _on_task_selected(self, index):
        """Handle task selection"""
        # Get the selected task
        item = self.task_model.itemFromIndex(index)
        if item:
            # TODO: Load the selected task in the editor pane
            print(f"Selected task: {item.text()}")
    
    def _on_add_task(self):
        """Handle add task button click"""
        # TODO: Show dialog to create new task
        item = QStandardItem("New Task")
        self.task_model.appendRow(item)
        print("Add task clicked")
    
    def _on_remove_task(self):
        """Handle remove task button click"""
        # Get the selected indices
        indices = self.task_list.selectedIndexes()
        if indices:
            # Remove the selected task
            for index in sorted(indices, reverse=True):
                self.task_model.removeRow(index.row())
            print("Task removed")
        else:
            print("No task selected") 