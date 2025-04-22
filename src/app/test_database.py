"""
Test module for database operations

This module tests the DatabaseManager class functionality
"""
import os
import unittest
import tempfile
import shutil
from pathlib import Path

from src.app.database import DatabaseManager
from src.models.video_task import VideoTask, Keyframe, Article
from src.models.template import Template
from src.app.constants import STATUS_PENDING, STATUS_COMPLETED, TONE_PROFESSIONAL


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        self.db_manager.initialize_database()
    
    def tearDown(self):
        """Clean up test environment"""
        # Disconnect from database
        self.db_manager.disconnect()
        
        # Remove test directory
        shutil.rmtree(self.test_dir)
    
    def test_connection(self):
        """Test database connection"""
        # Disconnect first to test reconnection
        self.db_manager.disconnect()
        
        # Test connection
        self.assertTrue(self.db_manager.connect())
        self.assertIsNotNone(self.db_manager.conn)
    
    def test_task_crud(self):
        """Test CRUD operations for VideoTask"""
        # Create a test task
        task = VideoTask.create_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        task.title = "Test Task"
        
        # Add a keyframe
        keyframe = Keyframe(
            timestamp="00:01:23",
            image_path="/tmp/keyframe.jpg",
            caption="Test caption"
        )
        task.add_keyframe(keyframe)
        
        # Add an article
        article = Article(
            title="Test Article",
            content="# Test Content\n\nThis is a test article."
        )
        task.set_article(article)
        
        # Save to database
        self.assertTrue(self.db_manager.save_task(task))
        
        # Retrieve from database
        retrieved_task = self.db_manager.get_task(task.id)
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task.id, task.id)
        self.assertEqual(retrieved_task.title, "Test Task")
        self.assertEqual(len(retrieved_task.keyframes), 1)
        self.assertEqual(retrieved_task.keyframes[0].timestamp, "00:01:23")
        self.assertIsNotNone(retrieved_task.article)
        self.assertEqual(retrieved_task.article.title, "Test Article")
        
        # Update task
        task.title = "Updated Task"
        task.update_status(STATUS_COMPLETED)
        self.assertTrue(self.db_manager.save_task(task))
        
        # Retrieve updated task
        updated_task = self.db_manager.get_task(task.id)
        self.assertIsNotNone(updated_task)
        self.assertEqual(updated_task.title, "Updated Task")
        self.assertEqual(updated_task.status, STATUS_COMPLETED)
        
        # Get all tasks
        all_tasks = self.db_manager.get_all_tasks()
        self.assertEqual(len(all_tasks), 1)
        
        # Get tasks by status
        completed_tasks = self.db_manager.get_all_tasks(STATUS_COMPLETED)
        self.assertEqual(len(completed_tasks), 1)
        pending_tasks = self.db_manager.get_all_tasks(STATUS_PENDING)
        self.assertEqual(len(pending_tasks), 0)
        
        # Delete task
        self.assertTrue(self.db_manager.delete_task(task.id))
        
        # Verify deletion
        self.assertIsNone(self.db_manager.get_task(task.id))
        all_tasks = self.db_manager.get_all_tasks()
        self.assertEqual(len(all_tasks), 0)
    
    def test_template_crud(self):
        """Test CRUD operations for Template"""
        # Create a test template
        template = Template(
            name="Test Template",
            tone=TONE_PROFESSIONAL,
            cta="Test call to action",
            brand="Test brand voice",
            structure="Test structure",
            css="body { font-family: Arial; }"
        )
        
        # Save to database
        self.assertTrue(self.db_manager.save_template(template))
        
        # Retrieve from database
        retrieved_template = self.db_manager.get_template(template.id)
        self.assertIsNotNone(retrieved_template)
        self.assertEqual(retrieved_template.id, template.id)
        self.assertEqual(retrieved_template.name, "Test Template")
        self.assertEqual(retrieved_template.tone, TONE_PROFESSIONAL)
        
        # Update template
        template.name = "Updated Template"
        self.assertTrue(self.db_manager.save_template(template))
        
        # Retrieve updated template
        updated_template = self.db_manager.get_template(template.id)
        self.assertIsNotNone(updated_template)
        self.assertEqual(updated_template.name, "Updated Template")
        
        # Get all templates
        all_templates = self.db_manager.get_all_templates()
        self.assertEqual(len(all_templates), 1)
        
        # Delete template
        self.assertTrue(self.db_manager.delete_template(template.id))
        
        # Verify deletion
        self.assertIsNone(self.db_manager.get_template(template.id))
        all_templates = self.db_manager.get_all_templates()
        self.assertEqual(len(all_templates), 0)
    
    def test_backup_restore(self):
        """Test database backup and restore"""
        # Create test data
        template = Template(name="Test Template", tone=TONE_PROFESSIONAL)
        self.db_manager.save_template(template)
        
        task = VideoTask.create_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.db_manager.save_task(task)
        
        # Create backup
        backup_path = os.path.join(self.test_dir, "backup.db")
        self.assertTrue(self.db_manager.backup_database(backup_path))
        self.assertTrue(os.path.exists(backup_path))
        
        # Delete all data
        self.db_manager.delete_template(template.id)
        self.db_manager.delete_task(task.id)
        all_templates = self.db_manager.get_all_templates()
        all_tasks = self.db_manager.get_all_tasks()
        self.assertEqual(len(all_templates), 0)
        self.assertEqual(len(all_tasks), 0)
        
        # Restore from backup
        self.assertTrue(self.db_manager.restore_database(backup_path))
        
        # Verify restored data
        all_templates = self.db_manager.get_all_templates()
        all_tasks = self.db_manager.get_all_tasks()
        self.assertEqual(len(all_templates), 1)
        self.assertEqual(len(all_tasks), 1)


if __name__ == "__main__":
    unittest.main() 