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

__all__ = [
    "SectionTemplate",
    "PromptAssembler",
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
    You are an experienced Medium author.  Produce engaging, well‑structured
    articles that follow Medium editorial guidelines:
    • Conversational yet authoritative tone
    • Clear headings (Title Case)
    • Short paragraphs (2‑4 sentences)
    • Use stories, data or quotes where appropriate
    • Include relevant call‑to‑action at the end

    Target audience is **informed general readers**; avoid jargon unless the
    topic demands it.
    """
)

_INTRO_TEMPLATE = _strip(
    """
    ### Introduction\n
    Briefly hook the reader by highlighting the main idea or problem. Use an
    anecdote or surprising statistic if possible.  End with a clear statement
    of what the article will cover.
    """
)

_BODY_TEMPLATE = _strip(
    """
    ### Main Points\n
    Elaborate on the key ideas extracted from the transcript.  Organise the
    content with sub‑headings.  For each point:
    1. Summarise the idea in one sentence.
    2. Provide supporting detail, examples or data (derived from the transcript).

    Keep language approachable; break up long explanations with lists or bolded
    terms.
    """
)

_CONCLUSION_TEMPLATE = _strip(
    """
    ### Conclusion\n
    Summarise the core takeaway in 2‑3 sentences.  End with a compelling CTA:
    "{cta}"
    """
)

# Register default section templates
DEFAULT_SECTIONS: List[SectionTemplate] = [
    SectionTemplate("system", _MEDIUM_SYSTEM_PROMPT),
    SectionTemplate("introduction", _INTRO_TEMPLATE),
    SectionTemplate("body", _BODY_TEMPLATE),
    SectionTemplate("conclusion", _CONCLUSION_TEMPLATE),
]


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


class PromptAssembler:
    """Combines `Template` and transcript into a full prompt string."""

    def __init__(self, *, sections: Optional[List[SectionTemplate]] = None):
        self.sections = sections or DEFAULT_SECTIONS

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
        vars_ = {
            "tone": template.tone,
            "brand": template.brand,
            "cta": template.cta or "Follow us for more insights",
        }

        for section in self.sections:
            rendered = section.render(**vars_)
            # Only system section is prefixed differently when used with chat API
            if section.name == "system":
                parts.append(rendered)
            else:
                parts.append(rendered)

        parts.append("\n### Source Transcript\n" + transcript_segment.strip())

        if extra_instructions:
            parts.append("\n### Additional Instructions\n" + extra_instructions.strip())

        return "\n\n".join(parts) 