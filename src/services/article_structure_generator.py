"""Article structure generator for YT-Article Craft.

Implements *task 4.6 (Implement article structure generation)* by providing
a service that generates well-structured articles with headings, paragraphs,
emphasis, and other formatting elements.

This service builds upon the SummarizerService to create more structured and
formatted articles with proper section organization, paragraph transitions,
and formatting elements like emphasis, quotes, and lists.

Key components:
- ArticleStructureGenerator - Service for generating structured articles
- ArticleFormatConfig - Configuration for article formatting preferences
"""

import logging
import re
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

from src.services.deepseek_service import DeepSeekService, DeepSeekError
from src.services.prompt_templates import PromptAssembler, SectionTemplate
from src.models.template import Template
from src.models.article_structure import (
    ArticleStructure, ArticleSection, ArticleElement,
    ArticleParagraph, ArticleList, ArticleQuote, ArticleOutline,
    Emphasis, EmphasisType
)


@dataclass
class ArticleFormatConfig:
    """Configuration for article formatting.
    
    Attributes:
        outline_mode (bool): Whether to generate an outline before content
        section_count (int): Target number of sections
        paragraph_density (str): Density of paragraphs ('low', 'medium', 'high')
        enhancement_level (str): Level of text enhancement ('minimal', 'balanced', 'extensive')
        list_frequency (str): Frequency of lists ('minimal', 'balanced', 'frequent')
        quote_frequency (str): Frequency of quotes ('none', 'minimal', 'balanced')
        export_format (str): Default export format ('markdown', 'html')
    """
    outline_mode: bool = True
    section_count: int = 5
    paragraph_density: str = "medium"
    enhancement_level: str = "balanced"
    list_frequency: str = "balanced"
    quote_frequency: str = "minimal"
    export_format: str = "markdown"


# Prompt templates for article structure generation
_OUTLINE_TEMPLATE = """
Create a well-structured outline for a {tone} style article on the topic described in the transcript below.
The article should follow Medium-style writing conventions and be organized to engage readers effectively.

Please provide:
1. A compelling article title (7-10 words)
2. {section_count} section headings (with a brief description of each section's content)

The outline should flow logically and cover the key points from the transcript while maintaining the {tone} tone.
Each section heading should be clear and engaging, using title case formatting.

TRANSCRIPT:
{transcript}

TEMPLATE TONE: {tone}
TEMPLATE BRAND VOICE: {brand}

RESPONSE FORMAT:
```json
{{
  "title": "Your Compelling Article Title Here",
  "sections": [
    {{ 
      "title": "First Section Heading",
      "description": "Brief description of what this section will cover."
    }},
    {{ 
      "title": "Second Section Heading",
      "description": "Brief description of what this section will cover."
    }},
    ...
  ]
}}
```

Remember to ensure the sections flow logically and cover all important aspects of the topic.
"""

_STRUCTURE_ENHANCEMENT_TEMPLATE = """
You are a content structure expert specializing in Medium-style articles. 
I'll provide you with article content that needs structural enhancement.

Your task is to transform this content into a well-structured article by:
1. Identifying natural section breaks and creating appropriate headings
2. Organizing paragraphs with smooth transitions
3. Adding appropriate emphasis (bold, italic) to key points and terms
4. Converting appropriate content into bulleted or numbered lists
5. Identifying quotes that would work well as blockquotes
6. Enhancing the introduction and conclusion

Enhancement level: {enhancement_level}
- For "minimal": Focus only on basic structure and mandatory formatting
- For "balanced": Apply a moderate amount of formatting and structural changes
- For "extensive": Apply comprehensive formatting and restructuring

CONTENT TO ENHANCE:
{content}

OUTLINE (reference only):
{outline}

RESPOND WITH A STRUCTURED JSON REPRESENTATION:
```json
{{
  "title": "Article Title",
  "intro": [
    {{
      "element_type": "paragraph",
      "text": "Introduction paragraph text...",
      "emphasis": [
        {{ "type": "bold", "start": 10, "end": 15 }}
      ]
    }},
    ...
  ],
  "sections": [
    {{
      "title": "Section Heading",
      "level": 2,
      "content": [
        {{
          "element_type": "paragraph",
          "text": "Section paragraph text..."
        }},
        {{
          "element_type": "list",
          "items": ["First item", "Second item"],
          "ordered": false
        }},
        {{
          "element_type": "quote",
          "text": "This is a blockquote",
          "source": "Optional source attribution"
        }},
        ...
      ]
    }},
    ...
  ],
  "conclusion": [
    {{
      "element_type": "paragraph",
      "text": "Conclusion paragraph text..."
    }},
    ...
  ]
}}
```

Ensure the enhanced structure maintains the original meaning and tone while improving readability and engagement.
"""


class ArticleStructureGenerator:
    """Service for generating structured articles.
    
    This service takes content from a summarizer and transforms it into
    well-structured articles with proper sections, formatting, and emphasis.
    """
    
    def __init__(
        self,
        deepseek_service: DeepSeekService,
        prompt_assembler: Optional[PromptAssembler] = None,
        config: Optional[ArticleFormatConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the article structure generator.
        
        Parameters
        ----------
        deepseek_service : DeepSeekService
            Service for interacting with DeepSeek API
        prompt_assembler : PromptAssembler, optional
            Service for assembling prompts
        config : ArticleFormatConfig, optional
            Configuration for article formatting
        logger : logging.Logger, optional
            Logger for the service
        """
        self.deepseek_service = deepseek_service
        self.prompt_assembler = prompt_assembler or PromptAssembler()
        self.config = config or ArticleFormatConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Register custom section templates
        self._outline_template = SectionTemplate(
            name="outline", 
            template=_OUTLINE_TEMPLATE
        )
        self._structure_enhancement_template = SectionTemplate(
            name="structure_enhancement", 
            template=_STRUCTURE_ENHANCEMENT_TEMPLATE
        )
    
    def generate_outline(
        self, 
        transcript: str, 
        template: Template,
        section_count: Optional[int] = None,
    ) -> ArticleOutline:
        """Generate an article outline with sections.
        
        Parameters
        ----------
        transcript : str
            Transcript to generate outline from
        template : Template
            Template for article style and tone
        section_count : int, optional
            Number of sections to generate (default from config)
            
        Returns
        -------
        ArticleOutline
            Generated outline with title and sections
        """
        section_count = section_count or self.config.section_count
        
        # Build prompt for outline generation
        outline_prompt = self._outline_template.render(
            transcript=transcript,
            tone=template.tone,
            brand=template.brand,
            section_count=section_count
        )
        
        try:
            # Generate outline using DeepSeek API
            self.logger.info(f"Generating article outline with {section_count} sections")
            response = self.deepseek_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a professional content outliner that creates structured article outlines."},
                    {"role": "user", "content": outline_prompt}
                ],
                model="deepseek-chat-6.7b",
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if not json_match:
                self.logger.warning("JSON structure not found in outline response")
                # Try to extract without code block markers
                json_data = response.strip()
            else:
                json_data = json_match.group(1)
            
            # Parse JSON
            try:
                outline_data = json.loads(json_data)
                
                # Validate required fields
                if "title" not in outline_data or "sections" not in outline_data:
                    raise ValueError("Missing required fields (title or sections) in outline data")
                
                # Create ArticleOutline
                return ArticleOutline(
                    title=outline_data["title"],
                    sections=outline_data["sections"],
                    metadata={"template_id": template.id}
                )
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse outline JSON: {e}")
                # Fallback to a basic outline
                return self._create_fallback_outline(transcript, template)
                
        except DeepSeekError as e:
            self.logger.error(f"DeepSeek API error during outline generation: {e}")
            # Fallback to a basic outline
            return self._create_fallback_outline(transcript, template)
    
    def _create_fallback_outline(
        self, 
        transcript: str, 
        template: Template
    ) -> ArticleOutline:
        """Create a fallback outline when API generation fails.
        
        Parameters
        ----------
        transcript : str
            Transcript to create outline from
        template : Template
            Template for article style
            
        Returns
        -------
        ArticleOutline
            Basic outline with generic sections
        """
        # Extract a title from the first few sentences
        first_sentences = " ".join(transcript.split(". ")[:3])
        title = f"Article About {first_sentences[:30]}..."
        
        # Create generic sections
        sections = [
            {"title": "Introduction", "description": "Introduction to the topic"},
            {"title": "Key Points", "description": "Main points from the transcript"},
            {"title": "Analysis", "description": "Analysis and insights"},
            {"title": "Practical Applications", "description": "How to apply this information"},
            {"title": "Conclusion", "description": "Summary and closing thoughts"}
        ]
        
        return ArticleOutline(
            title=title,
            sections=sections[:self.config.section_count],
            metadata={"template_id": template.id, "fallback": True}
        )
    
    def structure_content(
        self, 
        content: str, 
        outline: Optional[ArticleOutline] = None,
        template: Optional[Template] = None,
        enhancement_level: Optional[str] = None,
    ) -> ArticleStructure:
        """Transform content into a structured article.
        
        Parameters
        ----------
        content : str
            Raw article content to structure
        outline : ArticleOutline, optional
            Article outline to follow
        template : Template, optional
            Template for article style
        enhancement_level : str, optional
            Level of enhancement ('minimal', 'balanced', 'extensive')
            
        Returns
        -------
        ArticleStructure
            Structured article with sections, formatting, etc.
        """
        enhancement_level = enhancement_level or self.config.enhancement_level
        
        # Use outline title or extract from content
        title = outline.title if outline else self._extract_title(content)
        
        # Prepare outline string representation for the prompt
        outline_str = outline.to_markdown() if outline else ""
        
        # Build prompt for structure enhancement
        structure_prompt = self._structure_enhancement_template.render(
            content=content,
            outline=outline_str,
            enhancement_level=enhancement_level
        )
        
        try:
            # Generate structured content using DeepSeek API
            self.logger.info(f"Generating article structure with {enhancement_level} enhancement")
            response = self.deepseek_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a professional content editor that transforms content into well-structured articles."},
                    {"role": "user", "content": structure_prompt}
                ],
                model="deepseek-chat-6.7b",
                temperature=0.7,
                max_tokens=4000
            )
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if not json_match:
                self.logger.warning("JSON structure not found in structure response")
                # Fallback to basic structure
                return self._create_fallback_structure(content, title, outline)
            
            json_data = json_match.group(1)
            
            # Parse JSON
            try:
                structure_data = json.loads(json_data)
                
                # Create elements for each section from the structure data
                intro_elements = [
                    self._create_element_from_dict(element) 
                    for element in structure_data.get("intro", [])
                ]
                
                sections = [
                    ArticleSection(
                        title=section["title"],
                        content=[
                            self._create_element_from_dict(element) 
                            for element in section.get("content", [])
                        ],
                        level=section.get("level", 2)
                    )
                    for section in structure_data.get("sections", [])
                ]
                
                conclusion_elements = [
                    self._create_element_from_dict(element) 
                    for element in structure_data.get("conclusion", [])
                ]
                
                # Construct the ArticleStructure
                return ArticleStructure(
                    title=structure_data.get("title", title),
                    intro=intro_elements,
                    sections=sections,
                    conclusion=conclusion_elements,
                    metadata={
                        "template_id": template.id if template else None,
                        "outline_id": outline.metadata.get("id") if outline else None,
                        "enhancement_level": enhancement_level
                    }
                )
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.error(f"Failed to parse structure JSON: {e}")
                # Fallback to a basic structure
                return self._create_fallback_structure(content, title, outline)
                
        except DeepSeekError as e:
            self.logger.error(f"DeepSeek API error during structure generation: {e}")
            # Fallback to a basic structure
            return self._create_fallback_structure(content, title, outline)
    
    def _create_element_from_dict(self, element_dict: Dict[str, Any]) -> ArticleElement:
        """Create an appropriate ArticleElement from dictionary data.
        
        Parameters
        ----------
        element_dict : Dict[str, Any]
            Dictionary with element data
            
        Returns
        -------
        ArticleElement
            Created element instance
        """
        element_type = element_dict.get("element_type", "paragraph")
        
        if element_type == "paragraph":
            # Create paragraph with emphasis if specified
            emphasis_list = []
            for emph in element_dict.get("emphasis", []):
                try:
                    emphasis_list.append(Emphasis(
                        type=EmphasisType(emph["type"]),
                        start=emph["start"],
                        end=emph["end"],
                        metadata=emph.get("metadata", {})
                    ))
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Invalid emphasis data: {e}")
            
            return ArticleParagraph(
                text=element_dict["text"],
                emphasis=emphasis_list,
                metadata=element_dict.get("metadata", {})
            )
            
        elif element_type == "list":
            return ArticleList(
                items=element_dict["items"],
                ordered=element_dict.get("ordered", False),
                metadata=element_dict.get("metadata", {})
            )
            
        elif element_type == "quote":
            return ArticleQuote(
                text=element_dict["text"],
                source=element_dict.get("source", ""),
                metadata=element_dict.get("metadata", {})
            )
            
        else:
            # Default to paragraph
            self.logger.warning(f"Unknown element type: {element_type}, using paragraph")
            return ArticleParagraph(
                text=element_dict.get("text", ""),
                metadata=element_dict.get("metadata", {})
            )
    
    def _extract_title(self, content: str) -> str:
        """Extract a title from content.
        
        Parameters
        ----------
        content : str
            Content to extract title from
            
        Returns
        -------
        str
            Extracted title or generic title
        """
        # Try to find a markdown title (# Title)
        title_match = re.match(r'#\s+(.*?)(\n|$)', content)
        if title_match:
            return title_match.group(1).strip()
        
        # If no title found, use first sentence
        first_sentence = content.split('.')[0]
        if len(first_sentence) > 10:
            return first_sentence[:50] + ("..." if len(first_sentence) > 50 else "")
        
        # Fallback to generic title
        return "Generated Article"
    
    def _create_fallback_structure(
        self, 
        content: str, 
        title: str,
        outline: Optional[ArticleOutline] = None
    ) -> ArticleStructure:
        """Create a fallback structure when API generation fails.
        
        Parameters
        ----------
        content : str
            Content to structure
        title : str
            Article title
        outline : ArticleOutline, optional
            Article outline to follow
            
        Returns
        -------
        ArticleStructure
            Basic article structure
        """
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Determine intro (first 1-2 paragraphs)
        intro_count = min(2, len(paragraphs) // 5 + 1)
        intro = [ArticleParagraph(text=p) for p in paragraphs[:intro_count]]
        
        # Determine conclusion (last 1-2 paragraphs)
        conclusion_count = min(2, len(paragraphs) // 5 + 1)
        conclusion = [ArticleParagraph(text=p) for p in paragraphs[-conclusion_count:]]
        
        # Create sections based on outline or split remaining content
        body_paragraphs = paragraphs[intro_count:-conclusion_count] if conclusion_count > 0 else paragraphs[intro_count:]
        
        if outline and outline.sections:
            # Use outline sections
            section_count = len(outline.sections)
            paragraphs_per_section = max(1, len(body_paragraphs) // section_count)
            
            sections = []
            for i, section_info in enumerate(outline.sections):
                start_idx = i * paragraphs_per_section
                end_idx = start_idx + paragraphs_per_section if i < section_count - 1 else len(body_paragraphs)
                
                section_paragraphs = body_paragraphs[start_idx:end_idx]
                if section_paragraphs:
                    section_elements = [ArticleParagraph(text=p) for p in section_paragraphs]
                    sections.append(ArticleSection(
                        title=section_info["title"],
                        content=section_elements,
                        level=2
                    ))
        else:
            # Create generic sections
            section_count = min(3, max(1, len(body_paragraphs) // 3))
            paragraphs_per_section = max(1, len(body_paragraphs) // section_count)
            
            sections = []
            for i in range(section_count):
                start_idx = i * paragraphs_per_section
                end_idx = start_idx + paragraphs_per_section if i < section_count - 1 else len(body_paragraphs)
                
                section_paragraphs = body_paragraphs[start_idx:end_idx]
                if section_paragraphs:
                    section_elements = [ArticleParagraph(text=p) for p in section_paragraphs]
                    sections.append(ArticleSection(
                        title=f"Section {i+1}",
                        content=section_elements,
                        level=2
                    ))
        
        return ArticleStructure(
            title=title,
            intro=intro,
            sections=sections,
            conclusion=conclusion,
            metadata={"fallback": True}
        )
    
    def enhance_article(
        self, 
        structure: ArticleStructure, 
        enhancement_options: Optional[Dict[str, Any]] = None
    ) -> ArticleStructure:
        """Enhance an existing article structure with additional formatting.
        
        Parameters
        ----------
        structure : ArticleStructure
            Article structure to enhance
        enhancement_options : Dict[str, Any], optional
            Options for enhancement
            
        Returns
        -------
        ArticleStructure
            Enhanced article structure
        """
        # This is a simplified version for the current implementation
        # A full implementation would apply smart formatting, emphasis, etc.
        
        # For now, just add some basic emphasis to the first sentence of each paragraph
        enhanced_structure = ArticleStructure(
            title=structure.title,
            intro=self._enhance_elements(structure.intro),
            sections=[
                ArticleSection(
                    title=section.title,
                    content=self._enhance_elements(section.content),
                    level=section.level,
                    metadata=section.metadata
                )
                for section in structure.sections
            ],
            conclusion=self._enhance_elements(structure.conclusion),
            metadata=structure.metadata
        )
        
        return enhanced_structure
    
    def _enhance_elements(self, elements: List[ArticleElement]) -> List[ArticleElement]:
        """Apply enhancements to a list of elements.
        
        Parameters
        ----------
        elements : List[ArticleElement]
            Elements to enhance
            
        Returns
        -------
        List[ArticleElement]
            Enhanced elements
        """
        enhanced = []
        
        for element in elements:
            if isinstance(element, ArticleParagraph) and not element.emphasis:
                # Add emphasis to important words if not already emphasized
                text = element.text
                
                # Find potential emphasis targets (capitalized words, technical terms)
                emphasis = []
                
                # Simple heuristic: emphasize first sentence if it's short
                first_sentence_match = re.match(r'^([^.!?]+[.!?])\s', text)
                if first_sentence_match and len(first_sentence_match.group(1)) < 100:
                    emphasis.append(Emphasis(
                        type=EmphasisType.ITALIC,
                        start=0,
                        end=len(first_sentence_match.group(1))
                    ))
                
                # Add the enhanced paragraph
                enhanced.append(ArticleParagraph(
                    text=text,
                    emphasis=emphasis,
                    metadata=element.metadata
                ))
            else:
                # Keep other elements as is
                enhanced.append(element)
        
        return enhanced
    
    def export_to_format(
        self, 
        structure: ArticleStructure, 
        format: str = "markdown"
    ) -> str:
        """Export article structure to the specified format.
        
        Parameters
        ----------
        structure : ArticleStructure
            Article structure to export
        format : str
            Format to export to ('markdown', 'html')
            
        Returns
        -------
        str
            Formatted article string
        """
        if format.lower() == "html":
            return structure.to_html()
        else:  # Default to markdown
            return structure.to_markdown()
    
    def generate_structured_article(
        self,
        transcript: str,
        template: Template,
        content: Optional[str] = None,
        config: Optional[ArticleFormatConfig] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[ArticleStructure, str]:
        """Generate a complete structured article from transcript.
        
        This is the main method that combines outline generation,
        content structuring, and enhancement.
        
        Parameters
        ----------
        transcript : str
            Transcript to generate article from
        template : Template
            Template for article style
        content : str, optional
            Pre-generated content (if not provided, this method assumes it will
            be generated externally and focuses only on structure)
        config : ArticleFormatConfig, optional
            Configuration overrides
        progress_callback : Callable[[float, str], None], optional
            Callback for reporting progress
            
        Returns
        -------
        Tuple[ArticleStructure, str]
            Tuple of (structured article, formatted output)
        """
        config = config or self.config
        
        # Step 1: Generate outline
        if progress_callback:
            progress_callback(0.1, "Generating article outline...")
        
        if config.outline_mode:
            outline = self.generate_outline(
                transcript, 
                template,
                section_count=config.section_count
            )
        else:
            outline = None
        
        # Step 2: Structure content
        if progress_callback:
            progress_callback(0.5, "Structuring article content...")
        
        if content:
            structure = self.structure_content(
                content,
                outline=outline,
                template=template,
                enhancement_level=config.enhancement_level
            )
        else:
            # Create a placeholder structure with the outline
            # The actual content will need to be generated elsewhere
            self.logger.info("No content provided, creating placeholder structure")
            structure = self._create_placeholder_structure(outline, template)
            
        # Step 3: Export to desired format
        if progress_callback:
            progress_callback(0.9, "Formatting article...")
        
        formatted_output = self.export_to_format(structure, config.export_format)
        
        if progress_callback:
            progress_callback(1.0, "Article structure complete")
        
        return structure, formatted_output
    
    def _create_placeholder_structure(
        self, 
        outline: Optional[ArticleOutline],
        template: Template
    ) -> ArticleStructure:
        """Create a placeholder structure based on outline.
        
        Parameters
        ----------
        outline : ArticleOutline, optional
            Article outline
        template : Template
            Article template
            
        Returns
        -------
        ArticleStructure
            Placeholder structure
        """
        if not outline:
            # Create minimal outline
            outline = ArticleOutline(
                title="Article Title",
                sections=[
                    {"title": "Section 1", "description": "First section content"},
                    {"title": "Section 2", "description": "Second section content"},
                    {"title": "Section 3", "description": "Third section content"}
                ]
            )
        
        # Create placeholder content
        intro = [ArticleParagraph(
            text="Introduction placeholder. This will be replaced with actual content."
        )]
        
        sections = []
        for section in outline.sections:
            sections.append(ArticleSection(
                title=section["title"],
                content=[ArticleParagraph(
                    text=section.get("description", "Section content placeholder.")
                )],
                level=2
            ))
        
        conclusion = [ArticleParagraph(
            text="Conclusion placeholder. This will be replaced with actual content."
        )]
        
        return ArticleStructure(
            title=outline.title,
            intro=intro,
            sections=sections,
            conclusion=conclusion,
            metadata={
                "template_id": template.id,
                "placeholder": True
            }
        ) 