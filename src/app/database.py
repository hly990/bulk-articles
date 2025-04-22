"""
Database Manager

This module provides the DatabaseManager class for handling all database operations
including connection management, schema creation, and CRUD operations for models.
"""

import os
import sqlite3
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

from .constants import DEFAULT_DB_FILENAME, DB_VERSION

# Set up logging
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database errors"""
    pass

class DatabaseManager:
    """Manages database connections and operations"""
    
    SCHEMA_SQL = """
    -- Application settings
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    
    -- Templates
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        content TEXT NOT NULL,
        tone TEXT,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Video tasks
    CREATE TABLE IF NOT EXISTS video_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        video_url TEXT,
        video_path TEXT,
        thumbnail_path TEXT,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT  -- JSON string containing additional metadata
    );
    
    -- Keyframes for video tasks
    CREATE TABLE IF NOT EXISTS keyframes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        timestamp REAL NOT NULL,
        image_path TEXT NOT NULL,
        caption TEXT,
        FOREIGN KEY (task_id) REFERENCES video_tasks(id) ON DELETE CASCADE
    );
    
    -- Articles for video tasks
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        template_id INTEGER,
        tone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES video_tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
    );
    
    -- Initialize version in settings
    INSERT OR IGNORE INTO settings (key, value) VALUES ('db_version', '1');
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the database file. If None, uses the default path.
        """
        if db_path is None:
            # Use default path in user's home directory
            home_dir = Path.home()
            app_dir = home_dir / ".ytarticlecraft"
            app_dir.mkdir(exist_ok=True)
            self.db_path = str(app_dir / DEFAULT_DB_FILENAME)
        else:
            self.db_path = db_path
            
        self.conn = None
        self.connected = False
        
        # Connect to the database
        self.connect()
        
        # Initialize schema if needed
        self._initialize_schema()
    
    def connect(self) -> None:
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.connected = True
            logger.info(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            self.connected = False
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def disconnect(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.connected = False
            logger.info("Disconnected from database")
    
    def _ensure_connection(self) -> None:
        """Ensure the database connection is active."""
        if not self.connected or self.conn is None:
            self.connect()
    
    def _initialize_schema(self) -> None:
        """Initialize the database schema if it does not exist."""
        self._ensure_connection()
        try:
            cursor = self.conn.cursor()
            cursor.executescript(self.SCHEMA_SQL)
            self.conn.commit()
            logger.info("Database schema initialized")
        except sqlite3.Error as e:
            logger.error(f"Schema initialization error: {e}")
            raise DatabaseError(f"Failed to initialize database schema: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query with parameters.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            
        Returns:
            sqlite3.Cursor: Query cursor
        """
        self._ensure_connection()
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution error: {query}, {e}")
            raise DatabaseError(f"Failed to execute query: {e}")
    
    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.
        
        Args:
            script: SQL script string
        """
        self._ensure_connection()
        try:
            cursor = self.conn.cursor()
            cursor.executescript(script)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Script execution error: {e}")
            raise DatabaseError(f"Failed to execute script: {e}")
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self._ensure_connection()
        try:
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Commit error: {e}")
            raise DatabaseError(f"Failed to commit transaction: {e}")
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._ensure_connection()
        try:
            self.conn.rollback()
        except sqlite3.Error as e:
            logger.error(f"Rollback error: {e}")
            raise DatabaseError(f"Failed to rollback transaction: {e}")
    
    # Template CRUD operations
    def create_template(self, name: str, content: str, description: str = "", 
                        tone: str = None, tags: List[str] = None) -> int:
        """
        Create a new template.
        
        Args:
            name: Template name
            content: Template content
            description: Template description
            tone: Template tone
            tags: List of tags
            
        Returns:
            int: ID of the created template
        """
        tags_json = json.dumps(tags) if tags else None
        
        query = """
            INSERT INTO templates (name, description, content, tone, tags)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.execute_query(query, (name, description, content, tone, tags_json))
        self.commit()
        return cursor.lastrowid
    
    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Dict or None: Template data or None if not found
        """
        query = "SELECT * FROM templates WHERE id = ?"
        cursor = self.execute_query(query, (template_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        template = dict(row)
        
        # Parse JSON fields
        if template.get('tags'):
            template['tags'] = json.loads(template['tags'])
        else:
            template['tags'] = []
            
        return template
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all templates.
        
        Returns:
            List[Dict]: List of all templates
        """
        query = "SELECT * FROM templates ORDER BY name"
        cursor = self.execute_query(query)
        templates = []
        
        for row in cursor.fetchall():
            template = dict(row)
            
            # Parse JSON fields
            if template.get('tags'):
                template['tags'] = json.loads(template['tags'])
            else:
                template['tags'] = []
                
            templates.append(template)
            
        return templates
    
    def update_template(self, template_id: int, **kwargs) -> bool:
        """
        Update a template.
        
        Args:
            template_id: Template ID
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not kwargs:
            return False
            
        # Handle special fields
        if 'tags' in kwargs and isinstance(kwargs['tags'], list):
            kwargs['tags'] = json.dumps(kwargs['tags'])
            
        # Set updated_at timestamp
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build UPDATE query
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        query = f"UPDATE templates SET {fields} WHERE id = ?"
        
        # Execute query
        values = list(kwargs.values()) + [template_id]
        cursor = self.execute_query(query, tuple(values))
        self.commit()
        
        return cursor.rowcount > 0
    
    def delete_template(self, template_id: int) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        query = "DELETE FROM templates WHERE id = ?"
        cursor = self.execute_query(query, (template_id,))
        self.commit()
        
        return cursor.rowcount > 0
    
    # Video Task CRUD operations
    def create_task(self, title: str, video_url: str = None, status: str = "pending",
                   description: str = "", metadata: Dict[str, Any] = None) -> int:
        """
        Create a new video task.
        
        Args:
            title: Task title
            video_url: URL of the video
            status: Task status
            description: Task description
            metadata: Additional metadata
            
        Returns:
            int: ID of the created task
        """
        metadata_json = json.dumps(metadata) if metadata else None
        
        query = """
            INSERT INTO video_tasks 
            (title, description, video_url, status, metadata)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.execute_query(
            query, 
            (title, description, video_url, status, metadata_json)
        )
        self.commit()
        return cursor.lastrowid
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict or None: Task data or None if not found
        """
        query = "SELECT * FROM video_tasks WHERE id = ?"
        cursor = self.execute_query(query, (task_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        task = dict(row)
        
        # Parse JSON fields
        if task.get('metadata'):
            task['metadata'] = json.loads(task['metadata'])
        else:
            task['metadata'] = {}
            
        # Get associated keyframes
        keyframes_query = "SELECT * FROM keyframes WHERE task_id = ? ORDER BY timestamp"
        cursor = self.execute_query(keyframes_query, (task_id,))
        task['keyframes'] = [dict(row) for row in cursor.fetchall()]
        
        # Get associated articles
        articles_query = "SELECT * FROM articles WHERE task_id = ? ORDER BY created_at"
        cursor = self.execute_query(articles_query, (task_id,))
        task['articles'] = [dict(row) for row in cursor.fetchall()]
        
        return task
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            List[Dict]: List of all tasks
        """
        query = "SELECT * FROM video_tasks ORDER BY created_at DESC"
        cursor = self.execute_query(query)
        tasks = []
        
        for row in cursor.fetchall():
            task = dict(row)
            
            # Parse JSON fields
            if task.get('metadata'):
                task['metadata'] = json.loads(task['metadata'])
            else:
                task['metadata'] = {}
                
            # We don't load keyframes and articles here for performance
            tasks.append(task)
            
        return tasks
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """
        Update a task.
        
        Args:
            task_id: Task ID
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not kwargs:
            return False
            
        # Handle special fields
        if 'metadata' in kwargs and isinstance(kwargs['metadata'], dict):
            kwargs['metadata'] = json.dumps(kwargs['metadata'])
            
        # Set updated_at timestamp
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build UPDATE query
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        query = f"UPDATE video_tasks SET {fields} WHERE id = ?"
        
        # Execute query
        values = list(kwargs.values()) + [task_id]
        cursor = self.execute_query(query, tuple(values))
        self.commit()
        
        return cursor.rowcount > 0
    
    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task and all associated data.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        query = "DELETE FROM video_tasks WHERE id = ?"
        cursor = self.execute_query(query, (task_id,))
        self.commit()
        
        return cursor.rowcount > 0
    
    # Keyframe operations
    def add_keyframe(self, task_id: int, timestamp: float, image_path: str, 
                    caption: str = None) -> int:
        """
        Add a keyframe to a task.
        
        Args:
            task_id: Task ID
            timestamp: Timestamp of the keyframe
            image_path: Path to the keyframe image
            caption: Caption for the keyframe
            
        Returns:
            int: ID of the created keyframe
        """
        query = """
            INSERT INTO keyframes (task_id, timestamp, image_path, caption)
            VALUES (?, ?, ?, ?)
        """
        cursor = self.execute_query(query, (task_id, timestamp, image_path, caption))
        self.commit()
        return cursor.lastrowid
    
    def get_keyframes(self, task_id: int) -> List[Dict[str, Any]]:
        """
        Get all keyframes for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List[Dict]: List of keyframes
        """
        query = "SELECT * FROM keyframes WHERE task_id = ? ORDER BY timestamp"
        cursor = self.execute_query(query, (task_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # Article operations
    def add_article(self, task_id: int, title: str, content: str,
                   template_id: int = None, tone: str = None) -> int:
        """
        Add an article to a task.
        
        Args:
            task_id: Task ID
            title: Article title
            content: Article content
            template_id: Template ID
            tone: Article tone
            
        Returns:
            int: ID of the created article
        """
        query = """
            INSERT INTO articles (task_id, title, content, template_id, tone)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.execute_query(query, (task_id, title, content, template_id, tone))
        self.commit()
        return cursor.lastrowid
    
    def get_articles(self, task_id: int) -> List[Dict[str, Any]]:
        """
        Get all articles for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List[Dict]: List of articles
        """
        query = "SELECT * FROM articles WHERE task_id = ? ORDER BY created_at"
        cursor = self.execute_query(query, (task_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_article(self, article_id: int, **kwargs) -> bool:
        """
        Update an article.
        
        Args:
            article_id: Article ID
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not kwargs:
            return False
            
        # Set updated_at timestamp
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build UPDATE query
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        query = f"UPDATE articles SET {fields} WHERE id = ?"
        
        # Execute query
        values = list(kwargs.values()) + [article_id]
        cursor = self.execute_query(query, tuple(values))
        self.commit()
        
        return cursor.rowcount > 0
    
    # Settings operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Any: Setting value
        """
        query = "SELECT value FROM settings WHERE key = ?"
        cursor = self.execute_query(query, (key,))
        row = cursor.fetchone()
        
        if not row:
            return default
            
        return row['value']
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        # Convert value to string if it's not
        if not isinstance(value, str):
            value = str(value)
            
        query = """
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """
        self.execute_query(query, (key, value))
        self.commit()
    
    # Backup and restore
    def backup_database(self, backup_path: str) -> str:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Directory to store the backup
            
        Returns:
            str: Path to the backup file
        """
        self._ensure_connection()
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"ytarticlecraft_backup_{timestamp}.db"
        backup_file = os.path.join(backup_path, backup_filename)
        
        # Disconnect to ensure all data is written
        self.disconnect()
        
        # Copy the database file
        try:
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Database backed up to {backup_file}")
        except Exception as e:
            logger.error(f"Backup error: {e}")
            raise DatabaseError(f"Failed to backup database: {e}")
        finally:
            # Reconnect
            self.connect()
            
        return backup_file
    
    def restore_database(self, backup_file: str) -> None:
        """
        Restore database from a backup.
        
        Args:
            backup_file: Path to the backup file
        """
        if not os.path.exists(backup_file):
            raise DatabaseError(f"Backup file does not exist: {backup_file}")
            
        # Disconnect from the database
        self.disconnect()
        
        try:
            # Copy the backup file over the current database
            shutil.copy2(backup_file, self.db_path)
            logger.info(f"Database restored from {backup_file}")
        except Exception as e:
            logger.error(f"Restore error: {e}")
            raise DatabaseError(f"Failed to restore database: {e}")
        finally:
            # Reconnect to the restored database
            self.connect() 