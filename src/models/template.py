"""
Template model for YT-Article Craft

This module defines the Template data model for article generation templates.
"""

import uuid
import json
import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from src.app.constants import (
    TONE_PROFESSIONAL, TONE_CASUAL, TONE_STORYTELLING,
    TONE_TECHNICAL, TONE_EDUCATIONAL
)


@dataclass
class Template:
    """
    Template model for article generation
    
    Attributes:
        id: Unique identifier for the template
        name: Template name
        tone: Style/tone for the content (professional, casual, etc.)
        cta: Call to Action text
        brand: Brand voice description
        structure: Article structure description or JSON schema
        css: Custom CSS for styling the article
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata for the template
        version: Version of the template
    """
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tone: str = TONE_PROFESSIONAL
    cta: str = ""
    brand: str = ""
    structure: str = ""
    css: str = ""
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    
    def __post_init__(self):
        """Validate the template after initialization"""
        if not self.name:
            raise ValueError("Name is required for Template")
        
        valid_tones = [
            TONE_PROFESSIONAL,
            TONE_CASUAL,
            TONE_STORYTELLING,
            TONE_TECHNICAL,
            TONE_EDUCATIONAL
        ]
        
        if self.tone not in valid_tones:
            raise ValueError(f"Invalid tone: {self.tone}. Must be one of: {', '.join(valid_tones)}")
        
        if self.version < 1:
            raise ValueError("Version must be >= 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the template to a dictionary
        
        Returns:
            Dict containing the template data
        """
        result = {}
        for key, value in asdict(self).items():
            if key in ('created_at', 'updated_at'):
                result[key] = value.isoformat() if value else None
            else:
                result[key] = value
        return result
    
    def to_json(self) -> str:
        """
        Convert the template to a JSON string
        
        Returns:
            JSON string representation of the template
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """
        Create a Template instance from a dictionary
        
        Args:
            data: Dictionary containing template data
            
        Returns:
            Template instance
        """
        template_data = data.copy()
        
        # Convert timestamps back to datetime objects
        for dt_field in ('created_at', 'updated_at'):
            if dt_field in template_data and template_data[dt_field]:
                template_data[dt_field] = datetime.datetime.fromisoformat(template_data[dt_field])
        
        return cls(**template_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Template':
        """
        Create a Template instance from a JSON string
        
        Args:
            json_str: JSON string representation of the template
            
        Returns:
            Template instance
        """
        return cls.from_dict(json.loads(json_str))
    
    def clone(self, new_name: Optional[str] = None) -> 'Template':
        """
        Create a clone of this template with a new ID
        
        Args:
            new_name: Optional new name for the cloned template
            
        Returns:
            New Template instance with the same data (except ID and optionally name)
        """
        template_dict = self.to_dict()
        template_dict.pop('id')  # Remove ID to generate a new one
        
        if new_name:
            template_dict['name'] = new_name
        
        return Template.from_dict(template_dict)
    
    def bump_version(self):
        """Increment template version and update timestamp."""
        self.version += 1
        self.updated_at = datetime.datetime.now()
    
    @classmethod
    def create_default_templates(cls) -> List['Template']:
        """
        Factory method to create a set of default templates
        
        Returns:
            List of Template instances with predefined settings
        """
        templates = []
        
        # Professional template
        templates.append(cls(
            name="Professional",
            tone=TONE_PROFESSIONAL,
            cta="Contact us for more information",
            brand="Clear, precise, and authoritative voice with formal language",
            structure=json.dumps({
                "sections": [
                    {"type": "introduction", "length": "medium"},
                    {"type": "main_points", "count": 3, "length": "long"},
                    {"type": "conclusion", "length": "short"}
                ]
            }),
            css="""
            body { font-family: 'Arial', sans-serif; line-height: 1.6; }
            h1 { color: #333366; font-size: 2em; }
            h2 { color: #333366; font-size: 1.5em; }
            p { margin-bottom: 1em; }
            """
        ))
        
        # Casual template
        templates.append(cls(
            name="Casual",
            tone=TONE_CASUAL,
            cta="Drop us a line if you liked this article!",
            brand="Friendly, conversational voice with everyday language",
            structure=json.dumps({
                "sections": [
                    {"type": "hook", "length": "short"},
                    {"type": "story", "length": "medium"},
                    {"type": "key_takeaways", "count": 3, "length": "medium"},
                    {"type": "conclusion", "length": "medium"}
                ]
            }),
            css="""
            body { font-family: 'Georgia', serif; line-height: 1.8; }
            h1 { color: #5C9EAD; font-size: 2.2em; }
            h2 { color: #5C9EAD; font-size: 1.6em; }
            p { margin-bottom: 1.2em; }
            """
        ))
        
        # Storytelling template
        templates.append(cls(
            name="Storytelling",
            tone=TONE_STORYTELLING,
            cta="Share your own story in the comments!",
            brand="Engaging, narrative-driven voice with descriptive language",
            structure=json.dumps({
                "sections": [
                    {"type": "opening_scene", "length": "medium"},
                    {"type": "character_intro", "length": "medium"},
                    {"type": "conflict", "length": "long"},
                    {"type": "resolution", "length": "medium"},
                    {"type": "moral", "length": "short"}
                ]
            }),
            css="""
            body { font-family: 'Palatino Linotype', serif; line-height: 1.9; }
            h1 { color: #8B4513; font-size: 2.4em; font-style: italic; }
            h2 { color: #8B4513; font-size: 1.8em; }
            p { margin-bottom: 1.4em; text-indent: 1em; }
            p:first-of-type { text-indent: 0; }
            """
        ))
        
        # Technical template
        templates.append(cls(
            name="Technical",
            tone=TONE_TECHNICAL,
            cta="For technical support or further details, contact our team",
            brand="Precise, factual voice with specialized terminology",
            structure=json.dumps({
                "sections": [
                    {"type": "abstract", "length": "short"},
                    {"type": "introduction", "length": "medium"},
                    {"type": "methodology", "length": "long"},
                    {"type": "results", "length": "long"},
                    {"type": "discussion", "length": "medium"},
                    {"type": "conclusion", "length": "short"},
                    {"type": "references", "length": "medium"}
                ]
            }),
            css="""
            body { font-family: 'Roboto', sans-serif; line-height: 1.7; }
            h1 { color: #202124; font-size: 1.8em; }
            h2 { color: #202124; font-size: 1.4em; }
            p { margin-bottom: 1em; }
            code { background-color: #f1f3f4; padding: 2px 4px; border-radius: 3px; }
            """
        ))
        
        # Educational template
        templates.append(cls(
            name="Educational",
            tone=TONE_EDUCATIONAL,
            cta="Want to learn more? Check out our course offerings!",
            brand="Clear, instructive voice with explanatory language",
            structure=json.dumps({
                "sections": [
                    {"type": "learning_objectives", "length": "medium"},
                    {"type": "background", "length": "medium"},
                    {"type": "main_concepts", "count": 4, "length": "long"},
                    {"type": "examples", "count": 2, "length": "medium"},
                    {"type": "practice_questions", "count": 3, "length": "short"},
                    {"type": "summary", "length": "medium"}
                ]
            }),
            css="""
            body { font-family: 'Verdana', sans-serif; line-height: 1.8; }
            h1 { color: #4285F4; font-size: 2em; }
            h2 { color: #4285F4; font-size: 1.5em; }
            p { margin-bottom: 1.2em; }
            blockquote { border-left: 4px solid #4285F4; padding-left: 1em; margin-left: 0; }
            """
        ))
        
        return templates 