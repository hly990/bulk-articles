#!/usr/bin/env python
"""
Test script to demonstrate the ArticleStructure functionality.
This script shows how to create a structured article and convert
it to different formats (Markdown and HTML).
"""

import sys
import os
from typing import List

# Add src directory to path
sys.path.append(os.getcwd())

from src.models.article_structure import (
    ArticleStructure, ArticleSection, ArticleElement,
    ArticleParagraph, ArticleList, ArticleQuote, ArticleOutline,
    Emphasis, EmphasisType
)

def create_sample_article() -> ArticleStructure:
    """Create a sample article structure for demonstration."""
    
    # Create introduction paragraphs
    intro = [
        ArticleParagraph(
            text="Artificial Intelligence has transformed the way we interact with technology. From voice assistants to recommendation systems, AI is everywhere.",
            emphasis=[
                Emphasis(type=EmphasisType.BOLD, start=0, end=24)
            ]
        ),
        ArticleParagraph(
            text="In this article, we'll explore the impact of AI on various industries and how it's shaping our future."
        )
    ]
    
    # Create sections with content
    sections = [
        ArticleSection(
            title="The Evolution of AI",
            level=2,
            content=[
                ArticleParagraph(
                    text="AI has evolved significantly over the decades. From rule-based systems to machine learning and now deep learning, the journey has been remarkable.",
                    emphasis=[
                        Emphasis(type=EmphasisType.ITALIC, start=104, end=119)
                    ]
                ),
                ArticleList(
                    items=[
                        "Rule-based systems (1950s-1980s)",
                        "Machine Learning (1980s-2010s)",
                        "Deep Learning (2010s-present)"
                    ],
                    ordered=True
                )
            ]
        ),
        ArticleSection(
            title="AI in Healthcare",
            level=2,
            content=[
                ArticleParagraph(
                    text="Healthcare is one of the industries most impacted by AI. From diagnosis to treatment planning, AI is revolutionizing patient care."
                ),
                ArticleQuote(
                    text="AI won't replace doctors, but doctors who use AI will replace those who don't.",
                    source="Dr. Eric Topol, Cardiologist and Digital Medicine Researcher"
                ),
                ArticleParagraph(
                    text="Some key applications include medical imaging analysis, drug discovery, and personalized medicine."
                )
            ]
        )
    ]
    
    # Create conclusion
    conclusion = [
        ArticleParagraph(
            text="As AI continues to evolve, we can expect even more transformative changes across industries.",
            emphasis=[
                Emphasis(type=EmphasisType.BOLD, start=3, end=15)
            ]
        ),
        ArticleParagraph(
            text="The key will be ensuring that these advancements benefit humanity while addressing important ethical considerations."
        )
    ]
    
    # Create the article structure
    article = ArticleStructure(
        title="The Transformative Impact of Artificial Intelligence",
        intro=intro,
        sections=sections,
        conclusion=conclusion,
        metadata={
            "author": "AI Enthusiast",
            "tags": ["artificial intelligence", "technology", "future"]
        }
    )
    
    return article

def main():
    """Main function to demonstrate article structure functionality."""
    
    # Create a sample article
    article = create_sample_article()
    
    # Display article structure details
    print("===== ARTICLE STRUCTURE DEMO =====")
    print(f"Title: {article.title}")
    print(f"Metadata: {article.metadata}")
    print(f"Sections: {len(article.sections)}")
    print(f"Intro paragraphs: {len(article.intro)}")
    print(f"Conclusion paragraphs: {len(article.conclusion)}")
    print("\n")
    
    # Convert to Markdown
    markdown = article.to_markdown()
    print("===== MARKDOWN OUTPUT =====")
    print(markdown)
    print("\n")
    
    # Convert to HTML
    html = article.to_html()
    print("===== HTML OUTPUT =====")
    print(html)
    print("\n")
    
    # Convert to JSON and back
    json_str = article.to_json()
    print("===== JSON SERIALIZATION/DESERIALIZATION =====")
    print(f"JSON length: {len(json_str)} characters")
    
    # Recreate from JSON
    recreated = ArticleStructure.from_json(json_str)
    print(f"Recreated title: {recreated.title}")
    print(f"Sections preserved: {len(recreated.sections) == len(article.sections)}")
    print("\n")
    
    print("Demo completed successfully!")

if __name__ == "__main__":
    main() 