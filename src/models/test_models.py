"""
Test script for the YT-Article Craft data models

This script demonstrates and tests the basic functionality of the VideoTask and Template models.
Run this script to verify that the models are working as expected.
"""

import json
import datetime
import os
from src.models.video_task import VideoTask, Keyframe, Article
from src.models.template import Template
from src.app.constants import (
    STATUS_PENDING, STATUS_COMPLETED, STATUS_FAILED,
    TONE_PROFESSIONAL, TONE_CASUAL
)


def test_template_model():
    """Test the Template model functionality"""
    print("\n=== Testing Template Model ===")
    
    # Create a template
    template = Template(
        name="Test Template",
        tone=TONE_PROFESSIONAL,
        cta="Test call to action",
        brand="Test brand voice",
        structure="Test structure",
        css="body { font-family: Arial; }"
    )
    
    print(f"Created template: {template.name} (ID: {template.id})")
    print(f"Tone: {template.tone}")
    print(f"Created at: {template.created_at}")
    
    # Test serialization
    template_dict = template.to_dict()
    template_json = template.to_json()
    print(f"\nJSON serialization successful: {bool(template_json)}")
    
    # Test deserialization
    template2 = Template.from_dict(template_dict)
    template3 = Template.from_json(template_json)
    
    print(f"Deserialization successful (dict): {template2.name == template.name}")
    print(f"Deserialization successful (JSON): {template3.name == template.name}")
    
    # Test cloning
    cloned_template = template.clone(new_name="Cloned Template")
    print(f"\nCloned template: {cloned_template.name} (ID: {cloned_template.id})")
    print(f"IDs different: {cloned_template.id != template.id}")
    print(f"Attributes preserved: {cloned_template.tone == template.tone}")
    
    # Test version
    print(f"\nInitial version: {template.version}")
    template.bump_version()
    print(f"After bump_version: {template.version}")
    print(f"Updated timestamp changed: {template.updated_at > template.created_at}")
    
    # Test version validation
    try:
        invalid_template = Template(
            name="Invalid Template",
            version=0
        )
        print("ERROR: Should have raised ValueError for invalid version")
    except ValueError as e:
        print(f"Correctly caught invalid version: {e}")
    
    # Test default templates
    default_templates = Template.create_default_templates()
    print(f"\nCreated {len(default_templates)} default templates:")
    for t in default_templates:
        print(f"- {t.name} (tone: {t.tone})")


def test_keyframe_article_models():
    """Test Keyframe and Article classes"""
    print("\n=== Testing Keyframe and Article Models ===")
    
    # Create a keyframe
    keyframe = Keyframe(
        timestamp="00:01:23",
        image_path="/tmp/keyframe1.jpg",
        caption="A person explaining a concept",
        metadata={"confidence": 0.95}
    )
    
    print(f"Created keyframe: {keyframe.timestamp}")
    print(f"Caption: {keyframe.caption}")
    print(f"Metadata: {keyframe.metadata}")
    
    # Test serialization
    keyframe_dict = keyframe.to_dict()
    print(f"\nKeyframe serialization successful: {bool(keyframe_dict)}")
    
    # Test deserialization
    keyframe2 = Keyframe.from_dict(keyframe_dict)
    print(f"Keyframe deserialization successful: {keyframe2.timestamp == keyframe.timestamp}")
    print(f"Metadata preserved: {keyframe2.metadata.get('confidence') == 0.95}")
    
    # Create an article
    article = Article(
        title="Test Article",
        content="# Test Content\n\nThis is a test article.",
        template_id="template123",
        metadata={"word_count": 150}
    )
    
    print(f"\nCreated article: {article.title}")
    print(f"Template ID: {article.template_id}")
    print(f"Metadata: {article.metadata}")
    
    # Test serialization
    article_dict = article.to_dict()
    print(f"\nArticle serialization successful: {bool(article_dict)}")
    
    # Test deserialization
    article2 = Article.from_dict(article_dict)
    print(f"Article deserialization successful: {article2.title == article.title}")
    print(f"Content preserved: {len(article2.content) == len(article.content)}")
    print(f"Metadata preserved: {article2.metadata.get('word_count') == 150}")


def test_video_task_model():
    """Test the VideoTask model functionality"""
    print("\n=== Testing VideoTask Model ===")
    
    # Create a video task from URL
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    task = VideoTask.create_from_url(url)
    
    print(f"Created task: {task.id}")
    print(f"URL: {task.url}")
    print(f"Status: {task.status}")
    print(f"Created at: {task.created_at}")
    
    # Test status update
    task.update_status(STATUS_COMPLETED)
    print(f"\nUpdated status: {task.status}")
    print(f"Updated at changed: {task.updated_at != task.created_at}")
    
    # Add keyframes
    keyframe1 = Keyframe(
        timestamp="00:01:23",
        image_path="/tmp/keyframe1.jpg",
        caption="A man dancing"
    )
    
    keyframe2 = Keyframe(
        timestamp="00:02:45",
        image_path="/tmp/keyframe2.jpg",
        caption="Close-up shot"
    )
    
    task.add_keyframe(keyframe1)
    task.add_keyframe(keyframe2)
    
    print(f"\nAdded keyframes: {len(task.keyframes)}")
    for kf in task.keyframes:
        print(f"- {kf.timestamp}: {kf.caption}")
    
    # Create and set article
    article = Article(
        title="Never Gonna Give You Up",
        content="# Rick Astley\n\nThis is a classic music video...",
        template_id="template123"
    )
    task.set_article(article)
    
    print(f"\nArticle set: {task.article.title}")
    print(f"Template ID updated: {task.template_id == 'template123'}")
    
    # Test serialization
    task_dict = task.to_dict()
    task_json = task.to_json()
    print(f"\nJSON serialization successful: {bool(task_json)}")
    
    # Test deserialization
    task2 = VideoTask.from_dict(task_dict)
    task3 = VideoTask.from_json(task_json)
    
    print(f"Deserialization successful (dict): {task2.url == task.url}")
    print(f"Deserialization successful (JSON): {task3.url == task.url}")
    print(f"Keyframes preserved: {len(task3.keyframes) == len(task.keyframes)}")
    print(f"Article preserved: {task3.article.title == task.article.title}")
    
    # Test error case
    try:
        task.update_status("INVALID_STATUS")
        print("ERROR: Should have raised ValueError for invalid status")
    except ValueError as e:
        print(f"\nCorrectly caught invalid status: {e}")
    
    # Test cloning
    cloned_task = task.clone()
    print(f"\nCloned task: {cloned_task.id}")
    print(f"IDs different: {cloned_task.id != task.id}")
    print(f"URL preserved: {cloned_task.url == task.url}")
    print(f"Status reset: {cloned_task.status == STATUS_PENDING}")
    print(f"Keyframes reset: {len(cloned_task.keyframes) == 0}")
    print(f"Article reset: {cloned_task.article is None}")
    
    # Test save and load
    temp_dir = "./temp_test"
    os.makedirs(temp_dir, exist_ok=True)
    filepath = task.save(temp_dir)
    print(f"\nSaved task to: {filepath}")
    
    loaded_task = VideoTask.load(filepath)
    print(f"Loaded task ID: {loaded_task.id}")
    print(f"ID preserved: {loaded_task.id == task.id}")
    print(f"Keyframes loaded: {len(loaded_task.keyframes) == len(task.keyframes)}")
    print(f"Article loaded: {loaded_task.article.title == task.article.title}")
    
    # Test extracting video ID
    video_id = task.extract_video_id()
    print(f"\nExtracted video ID: {video_id}")
    print(f"Correct video ID: {video_id == 'dQw4w9WgXcQ'}")
    
    # Clean up test files
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"Removed test file: {filepath}")


def main():
    """Run all model tests"""
    print("=== YT-Article Craft Model Tests ===")
    
    test_template_model()
    test_keyframe_article_models()
    test_video_task_model()
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    main() 