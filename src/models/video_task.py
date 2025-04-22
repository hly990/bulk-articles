"""
VideoTask model for YT-Article Craft

This module defines the VideoTask class, which represents a video processing task.
"""
import os
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

from src.app.constants import (
    STATUS_PENDING, VALID_STATUSES, YOUTUBE_URL_PATTERN,
    DEFAULT_SAVE_DIRECTORY
)


@dataclass
class Keyframe:
    """
    Represents a keyframe from a video
    
    Attributes:
        timestamp (str): Timestamp in format HH:MM:SS
        image_path (str): Path to the keyframe image file
        caption (str): Generated caption for the keyframe
        metadata (dict): Additional keyframe metadata
    """
    timestamp: str
    image_path: str
    caption: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert keyframe to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Keyframe':
        """Create keyframe from dictionary"""
        return cls(
            timestamp=data["timestamp"],
            image_path=data["image_path"],
            caption=data.get("caption", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class Article:
    """
    Represents a generated article
    
    Attributes:
        title (str): Article title
        content (str): Article content (Markdown formatted)
        template_id (str): ID of the template used
        metadata (dict): Additional article metadata
    """
    title: str
    content: str
    template_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """Create article from dictionary"""
        return cls(
            title=data["title"],
            content=data["content"],
            template_id=data.get("template_id"),
            metadata=data.get("metadata", {})
        )


class VideoTask:
    """
    Represents a video processing task for creating articles from YouTube videos.
    
    Attributes:
        id (str): Unique identifier for the task
        url (str): YouTube video URL
        status (str): Current status of the task
        language (str): Language code for the video/article
        title (str): Video title
        description (str): Video description
        transcript (str): Transcribed text from the video
        keyframes (list): List of keyframe information (timestamps and descriptions)
        article (str): Generated article content
        template_id (str): ID of the template used for article generation
        created_at (str): ISO format timestamp of creation
        updated_at (str): ISO format timestamp of last update
        metadata (dict): Additional metadata for the task
    """
    
    def __init__(self, url, template_id=None, language="en", id=None, status=STATUS_PENDING,
                 title="", description="", transcript="", keyframes=None, article=None,
                 created_at=None, updated_at=None, metadata=None):
        """
        Initialize a new VideoTask.
        
        Args:
            url (str): YouTube video URL
            template_id (str, optional): ID of the template to use
            language (str, optional): Language code. Defaults to "en".
            id (str, optional): Task ID. Defaults to a new UUID.
            status (str, optional): Task status. Defaults to pending.
            title (str, optional): Video title. Defaults to empty string.
            description (str, optional): Video description. Defaults to empty string.
            transcript (str, optional): Transcribed text. Defaults to empty string.
            keyframes (list, optional): List of keyframes. Defaults to empty list.
            article (Article, optional): Generated article. Defaults to None.
            created_at (str, optional): Creation timestamp. Defaults to current time.
            updated_at (str, optional): Update timestamp. Defaults to current time.
            metadata (dict, optional): Additional metadata. Defaults to empty dict.
        """
        # Validate YouTube URL
        if not re.match(YOUTUBE_URL_PATTERN, url):
            raise ValueError("Invalid YouTube URL provided")
            
        # Required fields
        self.id = id if id else str(uuid.uuid4())
        self.url = url
        
        # Validate status
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status value: {status}")
        self.status = status
        
        # Optional fields with defaults
        self.language = language
        self.title = title
        self.description = description
        self.transcript = transcript
        self.keyframes = keyframes if keyframes is not None else []
        self.article = article
        self.template_id = template_id
        
        # Timestamps
        current_time = datetime.now().isoformat()
        self.created_at = created_at if created_at else current_time
        self.updated_at = updated_at if updated_at else current_time
        
        # Additional metadata
        self.metadata = metadata if metadata is not None else {}
    
    @classmethod
    def create_from_url(cls, url, template_id=None, language="en"):
        """
        Create a new VideoTask from a URL.
        
        Args:
            url (str): YouTube video URL
            template_id (str, optional): ID of the template to use
            language (str, optional): Language code. Defaults to "en".
            
        Returns:
            VideoTask: New VideoTask instance
        """
        return cls(url=url, template_id=template_id, language=language)
    
    def update_status(self, new_status):
        """
        Update the task status and updated_at timestamp.
        
        Args:
            new_status (str): New status value
            
        Raises:
            ValueError: If the status is invalid
        """
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status value: {new_status}")
        
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
    
    def add_keyframe(self, keyframe):
        """
        Add a keyframe to the task.
        
        Args:
            keyframe (Keyframe): Keyframe to add
        """
        self.keyframes.append(keyframe)
        self.updated_at = datetime.now().isoformat()
    
    def set_article(self, article):
        """
        Set the article for the task.
        
        Args:
            article (Article): Article instance
        """
        self.article = article
        if article.template_id and not self.template_id:
            self.template_id = article.template_id
        self.updated_at = datetime.now().isoformat()
    
    def update_article(self, article_content):
        """
        Update the article content and updated_at timestamp.
        
        Args:
            article_content (str): New article content
        """
        if self.article:
            self.article.content = article_content
        else:
            self.article = Article(title=self.title or "Article", content=article_content)
        self.updated_at = datetime.now().isoformat()
    
    def update_keyframes(self, keyframes):
        """
        Update the keyframes list and updated_at timestamp.
        
        Args:
            keyframes (list): New list of keyframes
        """
        self.keyframes = keyframes
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        """
        Convert the task to a dictionary for serialization.
        
        Returns:
            dict: Task data as a dictionary
        """
        result = {
            "id": self.id,
            "url": self.url,
            "status": self.status,
            "language": self.language,
            "title": self.title,
            "description": self.description,
            "transcript": self.transcript,
            "keyframes": [kf.to_dict() if hasattr(kf, 'to_dict') else kf for kf in self.keyframes],
            "template_id": self.template_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
        
        if self.article:
            result["article"] = self.article.to_dict() if hasattr(self.article, 'to_dict') else self.article
            
        return result
    
    def to_json(self):
        """
        Convert the task to a JSON string.
        
        Returns:
            str: JSON string representation of the task
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def save(self, directory=None):
        """
        Save the task to a JSON file.
        
        Args:
            directory (str, optional): Directory to save the file. 
                                       Defaults to DEFAULT_SAVE_DIRECTORY.
                                       
        Returns:
            str: Path to the saved file
        """
        if directory is None:
            directory = DEFAULT_SAVE_DIRECTORY
            
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Create filename based on task ID
        filename = f"task_{self.id}.json"
        filepath = os.path.join(directory, filename)
        
        # Save task data as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
        return filepath
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a VideoTask instance from a dictionary.
        
        Args:
            data (dict): Task data dictionary
            
        Returns:
            VideoTask: New VideoTask instance
        """
        # Process keyframes
        keyframes = []
        for kf_data in data.get("keyframes", []):
            if isinstance(kf_data, dict):
                keyframes.append(Keyframe.from_dict(kf_data))
            else:
                keyframes.append(kf_data)
                
        # Process article
        article = None
        article_data = data.get("article")
        if article_data:
            if isinstance(article_data, dict):
                article = Article.from_dict(article_data)
            else:
                article = article_data
        
        return cls(
            url=data["url"],
            id=data.get("id"),
            status=data.get("status", STATUS_PENDING),
            language=data.get("language", "en"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            transcript=data.get("transcript", ""),
            keyframes=keyframes,
            article=article,
            template_id=data.get("template_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str):
        """
        Create a VideoTask instance from a JSON string.
        
        Args:
            json_str (str): JSON string representation of task data
            
        Returns:
            VideoTask: New VideoTask instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def load(cls, filepath):
        """
        Load a task from a JSON file.
        
        Args:
            filepath (str): Path to the task JSON file
            
        Returns:
            VideoTask: Loaded VideoTask instance
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return cls.from_dict(data)
    
    @classmethod
    def list_saved_tasks(cls, directory=None):
        """
        List all saved tasks in the specified directory.
        
        Args:
            directory (str, optional): Directory to search. 
                                       Defaults to DEFAULT_SAVE_DIRECTORY.
                                       
        Returns:
            list: List of task filenames
        """
        if directory is None:
            directory = DEFAULT_SAVE_DIRECTORY
            
        if not os.path.exists(directory):
            return []
            
        return [f for f in os.listdir(directory) 
                if f.startswith("task_") and f.endswith(".json")]
    
    def clone(self):
        """
        Create a clone of this task with a new ID.
        
        Returns:
            VideoTask: New task instance with the same properties but a new ID
        """
        task_dict = self.to_dict()
        task_dict.pop("id")  # Remove ID to generate a new one
        
        # Set timestamps to current time
        current_time = datetime.now().isoformat()
        task_dict["created_at"] = current_time
        task_dict["updated_at"] = current_time
        
        # Reset progress-related fields
        task_dict["status"] = STATUS_PENDING
        task_dict["transcript"] = ""
        task_dict["keyframes"] = []
        task_dict["article"] = None
        
        return VideoTask.from_dict(task_dict)
    
    def extract_video_id(self):
        """
        Extract the YouTube video ID from the URL.
        
        Returns:
            str: YouTube video ID or None if not found
        """
        match = re.search(YOUTUBE_URL_PATTERN, self.url)
        if match:
            return match.group(1)
        return None
    
    def __str__(self):
        """String representation of the task."""
        return f"VideoTask(id={self.id}, url={self.url}, status={self.status})"
    
    def __repr__(self):
        """Detailed string representation."""
        return self.__str__() 