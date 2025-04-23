from __future__ import annotations
"""Prompt template utilities for article generation (task 4.3).

This module centralises all **prompt strings** and helper functions used when
interacting with LLMs (DeepSeek / local models).  By keeping them in one place
we can iterate on wording without touching service logic.

Key concepts
------------
* *SectionTemplate* – represents a reusable prompt snippet (intro, body …).
* *PromptAssembler* – combines a `Template` (tone / brand / CTA …) and the
  current **transcript segment** into a single prompt ready for the model.

We initially focus on *Medium‑style writing* but leave hooks for future styles.
"""

from dataclasses import dataclass
from textwrap import dedent
from typing import Dict, List, Optional

from src.models.template import Template
from src.app.constants import (
    TONE_PROFESSIONAL, TONE_CASUAL, TONE_STORYTELLING,
    TONE_TECHNICAL, TONE_EDUCATIONAL
)

__all__ = [
    "SectionTemplate",
    "PromptAssembler",
    "MEDIUM_TEMPLATES",
    "TONE_SPECIFIC_GUIDANCE",
    "DEFAULT_SECTIONS"
]


# ---------------------------------------------------------------------------
# Section template data
# ---------------------------------------------------------------------------


def _strip(s: str) -> str:  # helper to keep multiline literals nice
    return dedent(s).strip()


@dataclass
class SectionTemplate:
    """A single prompt section (system / intro / conclusion…)."""

    name: str  # e.g. "introduction"
    template: str  # Contains placeholders like {tone}, {cta}

    def render(self, **kwargs) -> str:  # noqa: D401
        """Return template with placeholders substituted."""
        return self.template.format(**kwargs)


# Medium‑style base templates -------------------------------------------------

_MEDIUM_SYSTEM_PROMPT = _strip(
    """
    You are an experienced Medium author with expertise in creating engaging, well-structured
    articles that captivate readers. Follow these Medium editorial guidelines:
    
    ## Style & Tone
    • Write in a {tone} tone that feels conversational yet authoritative
    • Use "you" and "I" to create a personal connection with readers
    • Maintain a balanced voice that represents {brand}
    • Avoid jargon and buzzwords unless necessary for technical topics
    
    ## Structure & Formatting
    • Create compelling headlines (7-10 words) that promise clear value
    • Use clear subheadings (Title Case) to organize content logically
    • Write short paragraphs (2-4 sentences max) with one idea per paragraph
    • Utilize formatting tools strategically:
      - **Bold** for emphasis on key points
      - *Italics* for introducing terms or subtle emphasis
      - > Blockquotes for important statements or quotes
      - Bulleted/numbered lists for scannable information
    
    ## Content Best Practices
    • Hook readers in the first paragraph with a surprising fact, question, or story
    • Support claims with data, examples, or personal experiences
    • Include stories, analogies or quotes where appropriate
    • Provide actionable insights throughout the article
    • End with a relevant call-to-action: "{cta}"
    
    Target audience: Informed general readers who are busy but curious to learn.
    """
)

_TITLE_TEMPLATE = _strip(
    """
    ### Title Generation
    
    Create an engaging title for this article that:
    - Is 7-10 words in length
    - Clearly communicates the main value or insight
    - Uses powerful words that create curiosity
    - Aligns with the {tone} tone
    - Optionally includes numbers or "How to" if appropriate
    
    Avoid clickbait while still making the title compelling enough to stand out.
    """
)

_INTRO_TEMPLATE = _strip(
    """
    ### Introduction
    
    Write an engaging introduction (2-3 paragraphs) that:
    - Opens with a hook: a compelling question, surprising statistic, or brief story
    - Establishes relevance to the reader's interests or needs
    - Hints at the problem or question the article will address
    - Introduces your perspective as it relates to {brand}
    - Ends with a clear thesis statement or promise of what the reader will learn
    
    Keep the tone {tone} and aim to have the reader nodding in agreement or curiosity
    by the end of the introduction. First paragraph should be especially short and punchy.
    """
)

_BODY_TEMPLATE = _strip(
    """
    ### Main Content
    
    Develop the article's main points by:
    - Organizing content under 3-5 clear subheadings (in Title Case)
    - Beginning each section with its most important idea
    - Supporting claims with evidence, examples, or relatable scenarios
    - Including personal insights where relevant
    - Using short paragraphs (2-4 sentences maximum)
    - Breaking up text with occasional:
      * Bulleted lists for multiple related points
      * Numbered lists for sequential steps
      * **Bold text** for key concepts
      * *Italic text* for emphasis
      * > Blockquotes for important statements
    
    Maintain a {tone} tone throughout and relate content to the perspectives of {brand}
    where appropriate. Aim for depth rather than breadth on key points.
    """
)

_CONCLUSION_TEMPLATE = _strip(
    """
    ### Conclusion
    
    Craft a satisfying conclusion that:
    - Summarizes the main insights (without simply repeating them)
    - Offers a fresh perspective or "big picture" view
    - Provides a practical next step or application
    - Ends with a compelling call-to-action: "{cta}"
    - Optionally poses a thought-provoking question to encourage comments
    
    Keep the conclusion concise (2-3 paragraphs) while still providing closure and
    a sense of value received.
    """
)

# Special purpose templates for specific needs ---------------------------------

_SEO_OPTIMIZATION_TEMPLATE = _strip(
    """
    ### SEO Optimization
    
    Enhance the article's discoverability by:
    - Integrating 2-3 relevant keywords naturally throughout the text
    - Using one primary keyword in the title, first paragraph, and at least one subheading
    - Including variations of keywords (synonyms, related terms)
    - Writing meta description that includes the primary keyword and communicates article value
    - Creating an SEO-friendly URL slug (3-5 words, including main keyword)
    
    Do this subtly, always prioritizing reader experience over keyword stuffing.
    """
)

_PULL_QUOTE_TEMPLATE = _strip(
    """
    ### Pull Quote Suggestion
    
    Identify 1-2 powerful sentences from the article that would make effective pull quotes.
    These should be:
    - Provocative, insightful, or emotionally resonant
    - Self-contained (understandable without additional context)
    - Representative of the article's core message
    - 1-2 sentences maximum
    
    Format these as blockquotes that could be highlighted visually within the article.
    """
)

# Tone-specific guidance ------------------------------------------------------

TONE_SPECIFIC_GUIDANCE = {
    TONE_PROFESSIONAL: {
        "intro": "Use industry-relevant examples and establish credibility early.",
        "body": "Balance factual information with practical insights. Maintain an authoritative but approachable voice.",
        "conclusion": "Emphasize professional benefits and actionable takeaways."
    },
    TONE_CASUAL: {
        "intro": "Open with a relatable anecdote or question that feels like a conversation starter.",
        "body": "Use everyday language, analogies, and examples that feel relatable and down-to-earth.",
        "conclusion": "Keep it friendly and encouraging, as if giving advice to a friend."
    },
    TONE_STORYTELLING: {
        "intro": "Begin with an intriguing narrative hook that sets the scene or introduces a character or situation.",
        "body": "Weave narrative elements throughout, using descriptive language and emotional touchpoints.",
        "conclusion": "Bring the story full circle and connect the narrative to the broader message."
    },
    TONE_TECHNICAL: {
        "intro": "Start with a clear problem statement or technical challenge that will be addressed.",
        "body": "Use precise terminology, code examples where relevant, and step-by-step explanations.",
        "conclusion": "Summarize technical insights and suggest specific applications or next steps."
    },
    TONE_EDUCATIONAL: {
        "intro": "Begin by establishing the learning objectives and why they matter to the reader.",
        "body": "Structure content as a progressive learning journey with clear explanations and examples.",
        "conclusion": "Reinforce key learnings and suggest ways to apply or extend the knowledge."
    }
}

# Register template collections -----------------------------------------------

# Default section templates
DEFAULT_SECTIONS: List[SectionTemplate] = [
    SectionTemplate("system", _MEDIUM_SYSTEM_PROMPT),
    SectionTemplate("title", _TITLE_TEMPLATE),
    SectionTemplate("introduction", _INTRO_TEMPLATE),
    SectionTemplate("body", _BODY_TEMPLATE),
    SectionTemplate("conclusion", _CONCLUSION_TEMPLATE),
]

# Optional specialized templates
OPTIONAL_SECTIONS: Dict[str, SectionTemplate] = {
    "seo": SectionTemplate("seo", _SEO_OPTIMIZATION_TEMPLATE),
    "pull_quote": SectionTemplate("pull_quote", _PULL_QUOTE_TEMPLATE),
}

# Complete collection of Medium templates
MEDIUM_TEMPLATES: Dict[str, SectionTemplate] = {
    "system": SectionTemplate("system", _MEDIUM_SYSTEM_PROMPT),
    "title": SectionTemplate("title", _TITLE_TEMPLATE),
    "introduction": SectionTemplate("introduction", _INTRO_TEMPLATE),
    "body": SectionTemplate("body", _BODY_TEMPLATE),
    "conclusion": SectionTemplate("conclusion", _CONCLUSION_TEMPLATE),
    "seo": SectionTemplate("seo", _SEO_OPTIMIZATION_TEMPLATE),
    "pull_quote": SectionTemplate("pull_quote", _PULL_QUOTE_TEMPLATE),
}


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


class PromptAssembler:
    """Combines `Template` and transcript into a full prompt string."""

    def __init__(
        self,
        *,
        sections: Optional[List[SectionTemplate]] = None,
        tone_guidance: Optional[Dict[str, Dict[str, str]]] = None,
        optional_sections: Optional[List[str]] = None
    ):
        """Initialize a PromptAssembler with customizable sections.
        
        Parameters
        ----------
        sections
            Base sections to include in every prompt
        tone_guidance
            Tone-specific guidance for different sections
        optional_sections
            Names of optional sections to include (e.g., "seo", "pull_quote")
        """
        self.sections = sections or DEFAULT_SECTIONS
        self.tone_guidance = tone_guidance or TONE_SPECIFIC_GUIDANCE
        
        # Add any optional sections requested
        if optional_sections:
            for section_name in optional_sections:
                if section_name in OPTIONAL_SECTIONS:
                    self.sections.append(OPTIONAL_SECTIONS[section_name])
        
    def _get_tone_guidance(self, tone: str, section: str) -> str:
        """Get tone-specific guidance for a particular section."""
        if tone in self.tone_guidance and section in self.tone_guidance[tone]:
            return self.tone_guidance[tone][section]
        return ""
        
    def build_prompt(
        self,
        *,
        template: Template,
        transcript_segment: str,
        extra_instructions: Optional[str] = None,
    ) -> str:
        """Return a ready‑to‑send prompt string.
        
        Parameters
        ----------
        template
            The user‑selected article Template containing tone / brand / CTA.
        transcript_segment
            Chunk of transcript text the model should summarise.
        extra_instructions
            Optional caller‑provided hints.
        """
        parts: List[str] = []
        
        # Base variables for all templates
        vars_ = {
            "tone": template.tone,
            "brand": template.brand or "a balanced, informative voice",
            "cta": template.cta or "Follow for more insights like these",
        }
        
        # Process each section
        for section in self.sections:
            # Add tone-specific guidance if available
            if section.name in ["introduction", "body", "conclusion"]:
                section_key = section.name
                if section_key == "introduction":
                    section_key = "intro"  # Match the key in TONE_SPECIFIC_GUIDANCE
                    
                tone_guidance = self._get_tone_guidance(template.tone, section_key)
                if tone_guidance:
                    enhanced_template = section.template + f"\n\nFor {template.tone} tone: {tone_guidance}"
                    rendered = SectionTemplate(section.name, enhanced_template).render(**vars_)
                else:
                    rendered = section.render(**vars_)
            else:
                rendered = section.render(**vars_)
                
            # Only system section is prefixed differently when used with chat API
            if section.name == "system":
                parts.append(rendered)
            else:
                parts.append(rendered)

        # Add transcript segment
        parts.append("\n### Source Transcript\n" + transcript_segment.strip())

        # Add any extra instructions
        if extra_instructions:
            parts.append("\n### Additional Instructions\n" + extra_instructions.strip())

        return "\n\n".join(parts) 