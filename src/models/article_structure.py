"""
Article structure models for YT-Article Craft

Implements *task 4.6 (Implement article structure generation)* by providing
models that support structured representation of articles with headings,
paragraphs, emphasis, and other formatting elements.

Key components:
- ArticleElement - Base class for article content elements
- ArticleParagraph - Represents a text paragraph with optional emphasis
- ArticleList - Represents an ordered or unordered list
- ArticleQuote - Represents a blockquote with optional source
- ArticleSection - Represents a section with a title and content elements
- ArticleStructure - Top-level article structure with intro, sections, and conclusion
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json
import re
import html


class EmphasisType(Enum):
    """Types of text emphasis"""
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    HIGHLIGHT = "highlight"
    CODE = "code"


@dataclass
class Emphasis:
    """
    Represents emphasis applied to a portion of text
    
    Attributes:
        type (EmphasisType): Type of emphasis
        start (int): Start position in text
        end (int): End position in text
        metadata (Dict): Additional metadata
    """
    type: EmphasisType
    start: int
    end: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert emphasis to dictionary for serialization"""
        result = {
            "type": self.type.value,
            "start": self.start,
            "end": self.end
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Emphasis':
        """Create emphasis from dictionary"""
        return cls(
            type=EmphasisType(data["type"]),
            start=data["start"],
            end=data["end"],
            metadata=data.get("metadata", {})
        )


# Changed from dataclass to regular class to avoid parameter ordering issues in inheritance
class ArticleElement:
    """
    Base class for article content elements
    
    Attributes:
        element_type (str): Type of element
        metadata (Dict): Additional metadata
    """
    def __init__(self, metadata: Dict[str, Any] = None):
        self.element_type = "base"
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert element to dictionary for serialization"""
        result = {
            "element_type": self.element_type
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    def to_markdown(self) -> str:
        """Convert element to Markdown format"""
        raise NotImplementedError("Subclasses must implement to_markdown")
    
    def to_html(self) -> str:
        """Convert element to HTML format"""
        raise NotImplementedError("Subclasses must implement to_html")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleElement':
        """Create appropriate element from dictionary based on element_type"""
        element_type = data["element_type"]
        if element_type == "paragraph":
            return ArticleParagraph.from_dict(data)
        elif element_type == "list":
            return ArticleList.from_dict(data)
        elif element_type == "quote":
            return ArticleQuote.from_dict(data)
        else:
            raise ValueError(f"Unknown element type: {element_type}")


@dataclass
class ArticleParagraph:
    """
    Represents a paragraph of text with optional emphasis
    
    Attributes:
        text (str): The paragraph text
        emphasis (List[Emphasis]): List of emphasis applied to text
        metadata (Dict): Additional metadata
    """
    text: str
    emphasis: List[Emphasis] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.element_type = "paragraph"
        self._element = ArticleElement(metadata=self.metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paragraph to dictionary for serialization"""
        result = {
            "element_type": self.element_type,
            "text": self.text
        }
        if self.metadata:
            result["metadata"] = self.metadata
        if self.emphasis:
            result["emphasis"] = [e.to_dict() for e in self.emphasis]
        return result
    
    def to_markdown(self) -> str:
        """Convert paragraph to Markdown format with emphasis"""
        if not self.emphasis:
            return self.text
        
        # Sort emphasis by start position (descending) to apply from end to beginning
        sorted_emphasis = sorted(self.emphasis, key=lambda e: e.start, reverse=True)
        result = self.text
        
        for emph in sorted_emphasis:
            start_marker = ""
            end_marker = ""
            
            if emph.type == EmphasisType.BOLD:
                start_marker = end_marker = "**"
            elif emph.type == EmphasisType.ITALIC:
                start_marker = end_marker = "*"
            elif emph.type == EmphasisType.CODE:
                start_marker = end_marker = "`"
            
            if start_marker:
                result = (
                    result[:emph.start] + 
                    start_marker + 
                    result[emph.start:emph.end] + 
                    end_marker + 
                    result[emph.end:]
                )
        
        return result
    
    def to_html(self) -> str:
        """Convert paragraph to HTML format with emphasis"""
        if not self.emphasis:
            return f"<p>{html.escape(self.text)}</p>"
        
        # Sort emphasis by start position (descending) to apply from end to beginning
        sorted_emphasis = sorted(self.emphasis, key=lambda e: e.start, reverse=True)
        text = html.escape(self.text)
        
        for emph in sorted_emphasis:
            start_tag = ""
            end_tag = ""
            
            if emph.type == EmphasisType.BOLD:
                start_tag = "<strong>"
                end_tag = "</strong>"
            elif emph.type == EmphasisType.ITALIC:
                start_tag = "<em>"
                end_tag = "</em>"
            elif emph.type == EmphasisType.UNDERLINE:
                start_tag = "<u>"
                end_tag = "</u>"
            elif emph.type == EmphasisType.HIGHLIGHT:
                start_tag = "<mark>"
                end_tag = "</mark>"
            elif emph.type == EmphasisType.CODE:
                start_tag = "<code>"
                end_tag = "</code>"
            
            if start_tag:
                text = (
                    text[:emph.start] + 
                    start_tag + 
                    text[emph.start:emph.end] + 
                    end_tag + 
                    text[emph.end:]
                )
        
        return f"<p>{text}</p>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleParagraph':
        """Create paragraph from dictionary"""
        emphasis = []
        if "emphasis" in data:
            emphasis = [Emphasis.from_dict(e) for e in data["emphasis"]]
        
        return cls(
            text=data["text"],
            emphasis=emphasis,
            metadata=data.get("metadata", {})
        )


@dataclass
class ArticleList:
    """
    Represents a list of items
    
    Attributes:
        items (List[str]): List items
        ordered (bool): Whether the list is ordered (numbered) or unordered (bullets)
        metadata (Dict): Additional metadata
    """
    items: List[str]
    ordered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.element_type = "list"
        self._element = ArticleElement(metadata=self.metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert list to dictionary for serialization"""
        result = {
            "element_type": self.element_type,
            "items": self.items,
            "ordered": self.ordered
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    def to_markdown(self) -> str:
        """Convert list to Markdown format"""
        result = []
        for i, item in enumerate(self.items):
            if self.ordered:
                result.append(f"{i+1}. {item}")
            else:
                result.append(f"- {item}")
        return "\n".join(result)
    
    def to_html(self) -> str:
        """Convert list to HTML format"""
        tag = "ol" if self.ordered else "ul"
        items_html = "\n".join([f"<li>{html.escape(item)}</li>" for item in self.items])
        return f"<{tag}>\n{items_html}\n</{tag}>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleList':
        """Create list from dictionary"""
        return cls(
            items=data["items"],
            ordered=data.get("ordered", False),
            metadata=data.get("metadata", {})
        )


@dataclass
class ArticleQuote:
    """
    Represents a blockquote
    
    Attributes:
        text (str): Quote text
        source (str): Quote source or attribution
        metadata (Dict): Additional metadata
    """
    text: str
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.element_type = "quote"
        self._element = ArticleElement(metadata=self.metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quote to dictionary for serialization"""
        result = {
            "element_type": self.element_type,
            "text": self.text
        }
        if self.source:
            result["source"] = self.source
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    def to_markdown(self) -> str:
        """Convert quote to Markdown format"""
        result = f"> {self.text}"
        if self.source:
            result += f"\n>\n> — {self.source}"
        return result
    
    def to_html(self) -> str:
        """Convert quote to HTML format"""
        quote_html = html.escape(self.text)
        if self.source:
            source_html = html.escape(self.source)
            return f"<blockquote>\n<p>{quote_html}</p>\n<footer>— {source_html}</footer>\n</blockquote>"
        return f"<blockquote>\n<p>{quote_html}</p>\n</blockquote>"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleQuote':
        """Create quote from dictionary"""
        return cls(
            text=data["text"],
            source=data.get("source", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class ArticleSection:
    """
    Represents a section of the article with a heading and content
    
    Attributes:
        title (str): Section title (heading)
        content (List[ArticleElement]): Section content elements
        level (int): Heading level (1 for main title, 2 for section, 3 for subsection)
        metadata (Dict): Additional metadata
    """
    title: str
    content: List[Union[ArticleParagraph, ArticleList, ArticleQuote]]
    level: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary for serialization"""
        return {
            "title": self.title,
            "content": [e.to_dict() for e in self.content],
            "level": self.level,
            "metadata": self.metadata if self.metadata else {}
        }
    
    def to_markdown(self) -> str:
        """Convert section to Markdown format"""
        heading = "#" * self.level
        result = [f"{heading} {self.title}"]
        
        for element in self.content:
            result.append(element.to_markdown())
        
        return "\n\n".join(result)
    
    def to_html(self) -> str:
        """Convert section to HTML format"""
        heading_html = html.escape(self.title)
        result = [f"<h{self.level}>{heading_html}</h{self.level}>"]
        
        for element in self.content:
            result.append(element.to_html())
        
        return "\n".join(result)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleSection':
        """Create section from dictionary"""
        content = []
        for item in data["content"]:
            element_type = item.get("element_type", "")
            if element_type == "paragraph":
                content.append(ArticleParagraph.from_dict(item))
            elif element_type == "list":
                content.append(ArticleList.from_dict(item))
            elif element_type == "quote":
                content.append(ArticleQuote.from_dict(item))
            else:
                raise ValueError(f"Unknown element type: {element_type}")
                
        return cls(
            title=data["title"],
            content=content,
            level=data.get("level", 2),
            metadata=data.get("metadata", {})
        )


@dataclass
class ArticleOutline:
    """
    Represents an article outline with title and section headings
    
    Attributes:
        title (str): Article title
        sections (List[Dict]): List of section titles and optional descriptions
        metadata (Dict): Additional metadata
    """
    title: str
    sections: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert outline to dictionary for serialization"""
        return {
            "title": self.title,
            "sections": self.sections,
            "metadata": self.metadata if self.metadata else {}
        }
    
    def to_markdown(self) -> str:
        """Convert outline to Markdown format"""
        result = [f"# {self.title}", ""]
        
        for i, section in enumerate(self.sections):
            result.append(f"## {i+1}. {section['title']}")
            if "description" in section and section["description"]:
                result.append(f"{section['description']}")
            result.append("")
        
        return "\n".join(result)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleOutline':
        """Create outline from dictionary"""
        return cls(
            title=data["title"],
            sections=data["sections"],
            metadata=data.get("metadata", {})
        )


@dataclass
class ArticleStructure:
    """
    Represents a structured article with title, intro, sections, and conclusion
    
    Attributes:
        title (str): Article title
        intro (List[ArticleElement]): Introduction elements
        sections (List[ArticleSection]): Article sections
        conclusion (List[ArticleElement]): Conclusion elements
        metadata (Dict): Additional metadata like SEO info, tags, etc.
    """
    title: str
    intro: List[Union[ArticleParagraph, ArticleList, ArticleQuote]]
    sections: List[ArticleSection]
    conclusion: List[Union[ArticleParagraph, ArticleList, ArticleQuote]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert structure to dictionary for serialization"""
        return {
            "title": self.title,
            "intro": [e.to_dict() for e in self.intro],
            "sections": [s.to_dict() for s in self.sections],
            "conclusion": [e.to_dict() for e in self.conclusion],
            "metadata": self.metadata if self.metadata else {}
        }
    
    def to_json(self) -> str:
        """Convert structure to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_markdown(self) -> str:
        """Convert structure to Markdown format"""
        result = [f"# {self.title}", ""]
        
        # Introduction
        for element in self.intro:
            result.append(element.to_markdown())
        
        result.append("")  # Extra line after intro
        
        # Sections
        for section in self.sections:
            result.append(section.to_markdown())
            result.append("")  # Extra line after each section
        
        # Conclusion
        if self.conclusion:
            result.append("## Conclusion")
            result.append("")
            for element in self.conclusion:
                result.append(element.to_markdown())
        
        return "\n\n".join(result)
    
    def to_html(self) -> str:
        """Convert structure to HTML format"""
        title_html = html.escape(self.title)
        result = [f"<h1>{title_html}</h1>"]
        
        # Introduction div
        result.append("<div class='article-intro'>")
        for element in self.intro:
            result.append(element.to_html())
        result.append("</div>")
        
        # Sections
        result.append("<div class='article-body'>")
        for section in self.sections:
            result.append(section.to_html())
        result.append("</div>")
        
        # Conclusion
        if self.conclusion:
            result.append("<div class='article-conclusion'>")
            result.append("<h2>Conclusion</h2>")
            for element in self.conclusion:
                result.append(element.to_html())
            result.append("</div>")
        
        return "\n".join(result)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleStructure':
        """Create structure from dictionary"""
        intro = []
        for item in data["intro"]:
            element_type = item.get("element_type", "")
            if element_type == "paragraph":
                intro.append(ArticleParagraph.from_dict(item))
            elif element_type == "list":
                intro.append(ArticleList.from_dict(item))
            elif element_type == "quote":
                intro.append(ArticleQuote.from_dict(item))
            else:
                raise ValueError(f"Unknown element type: {element_type}")
                
        sections = [ArticleSection.from_dict(s) for s in data["sections"]]
        
        conclusion = []
        for item in data["conclusion"]:
            element_type = item.get("element_type", "")
            if element_type == "paragraph":
                conclusion.append(ArticleParagraph.from_dict(item))
            elif element_type == "list":
                conclusion.append(ArticleList.from_dict(item))
            elif element_type == "quote":
                conclusion.append(ArticleQuote.from_dict(item))
            else:
                raise ValueError(f"Unknown element type: {element_type}")
        
        return cls(
            title=data["title"],
            intro=intro,
            sections=sections,
            conclusion=conclusion,
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ArticleStructure':
        """Create structure from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_markdown(cls, markdown: str) -> 'ArticleStructure':
        """Create structure from Markdown text (experimental)"""
        # This is a simplified parser for demonstration
        lines = markdown.split("\n")
        title = ""
        intro = []
        sections = []
        conclusion = []
        current_section = None
        current_text = []
        in_conclusion = False
        
        for line in lines:
            # Main title
            if line.startswith("# "):
                title = line[2:].strip()
            
            # Section headings
            elif line.startswith("## "):
                # Save previous section if exists
                if current_section:
                    text = "\n".join(current_text).strip()
                    if text:
                        current_section.content.append(
                            ArticleParagraph(text=text)
                        )
                    sections.append(current_section)
                    current_text = []
                
                # Check if this is conclusion
                if "conclusion" in line.lower():
                    in_conclusion = True
                    continue
                
                # Create new section
                current_section = ArticleSection(
                    title=line[3:].strip(),
                    content=[],
                    level=2
                )
            
            # Regular content
            else:
                if line.strip():
                    current_text.append(line)
                elif current_text:  # Empty line after content
                    text = "\n".join(current_text).strip()
                    if text:
                        if not title:  # If no title yet, this is initial content
                            intro.append(ArticleParagraph(text=text))
                        elif in_conclusion:
                            conclusion.append(ArticleParagraph(text=text))
                        elif current_section:
                            current_section.content.append(
                                ArticleParagraph(text=text)
                            )
                    current_text = []
        
        # Handle remaining text
        if current_text:
            text = "\n".join(current_text).strip()
            if text:
                if in_conclusion:
                    conclusion.append(ArticleParagraph(text=text))
                elif current_section:
                    current_section.content.append(
                        ArticleParagraph(text=text)
                    )
                else:
                    intro.append(ArticleParagraph(text=text))
        
        # Add final section if needed
        if current_section and not in_conclusion:
            sections.append(current_section)
        
        return cls(
            title=title,
            intro=intro,
            sections=sections,
            conclusion=conclusion
        )