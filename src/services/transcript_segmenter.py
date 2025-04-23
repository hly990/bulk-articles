from __future__ import annotations

"""Transcript segmentation service for long video transcripts.

Implements *task 4.4 (Build transcript segmentation functionality)* by providing:

* `TranscriptSegmenter` - Service for breaking long transcripts into manageable segments
* `Segment` - Data model for transcript segments with metadata
* `SegmentManager` - Manager for processing multiple segments

This service handles segmentation of lengthy video transcripts into smaller chunks
that can be processed within token limits of AI models like DeepSeek.
"""

import re
import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Callable, Iterator

__all__ = [
    "TranscriptSegmenter",
    "Segment",
    "SegmentManager",
    "TokenizerInterface"
]


# ---------------------------------------------------------------------------
# Tokenizer Interface
# ---------------------------------------------------------------------------

class TokenizerInterface:
    """Interface for text tokenizers.
    
    This abstract class defines the interface that any tokenizer must implement
    to be used with the TranscriptSegmenter.
    """
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text.
        
        Parameters
        ----------
        text : str
            The text to tokenize
            
        Returns
        -------
        int
            The number of tokens in the text
        """
        raise NotImplementedError("Tokenizer must implement count_tokens method")
    
    def truncate_text_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit.
        
        Parameters
        ----------
        text : str
            The text to truncate
        max_tokens : int
            Maximum number of tokens allowed
            
        Returns
        -------
        str
            Truncated text that fits within token limit
        """
        raise NotImplementedError("Tokenizer must implement truncate_text_to_tokens method")


# ---------------------------------------------------------------------------
# Simple Tokenizer Implementation
# ---------------------------------------------------------------------------

class SimpleTokenizer(TokenizerInterface):
    """Simple tokenizer that approximates token count based on whitespace.
    
    This is a basic implementation that provides a reasonable approximation
    for token counting when a more sophisticated tokenizer is not available.
    """
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using simple whitespace-based approach.
        
        Parameters
        ----------
        text : str
            Text to tokenize
            
        Returns
        -------
        int
            Approximated token count
        """
        if not text:
            return 0
        
        # 计算中文字符数量
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # Split by whitespace for a basic word count
        words = text.split()
        
        # Add extra tokens for punctuation and special characters
        punctuation_count = len(re.findall(r'[,.!?;:，。！？；：]', text))
        
        # Base multiplier - LLM tokens are typically smaller than words
        # This is a very rough approximation
        base_count = len(words) + punctuation_count + chinese_chars
        
        # Apply a multiplier to account for subword tokenization
        # Most LLMs will use more tokens than words
        return int(base_count * 1.25)
    
    def truncate_text_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token count.
        
        Parameters
        ----------
        text : str
            Text to truncate
        max_tokens : int
            Maximum number of tokens
            
        Returns
        -------
        str
            Truncated text
        """
        if not text:
            return ""
        
        # If text is already under the limit, return as is
        if self.count_tokens(text) <= max_tokens:
            return text
        
        # Simple approach: truncate by words and check token count
        words = text.split()
        current_text = ""
        
        for i, word in enumerate(words):
            temp_text = current_text + " " + word if current_text else word
            if self.count_tokens(temp_text) > max_tokens:
                break
            current_text = temp_text
        
        return current_text


# ---------------------------------------------------------------------------
# Segment Data Model
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    """A segment of transcript text with metadata.
    
    Attributes
    ----------
    text : str
        The segment's text content
    segment_id : int
        Unique identifier for this segment in the sequence
    total_segments : int
        Total number of segments in the sequence
    start_pos : int
        Character position in the original transcript where this segment starts
    end_pos : int
        Character position in the original transcript where this segment ends
    token_count : int
        Number of tokens in this segment
    overlap_before : int
        Number of overlapping characters with the previous segment
    overlap_after : int
        Number of overlapping characters with the next segment
    metadata : Dict[str, Any]
        Additional metadata for this segment
    """
    
    text: str
    segment_id: int
    total_segments: int
    start_pos: int
    end_pos: int
    token_count: int
    overlap_before: int = 0
    overlap_after: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_first(self) -> bool:
        """Check if this is the first segment."""
        return self.segment_id == 1
    
    @property
    def is_last(self) -> bool:
        """Check if this is the last segment."""
        return self.segment_id == self.total_segments
    
    @property
    def length(self) -> int:
        """Get the length of the segment text in characters."""
        return len(self.text)


# ---------------------------------------------------------------------------
# Segment Manager
# ---------------------------------------------------------------------------

class SegmentManager:
    """Manager for processing multiple transcript segments.
    
    This class provides utilities for working with a collection of segments,
    including iteration, access, and batch processing.
    """
    
    def __init__(self, segments: List[Segment] = None):
        """Initialize the segment manager.
        
        Parameters
        ----------
        segments : List[Segment], optional
            Initial list of segments to manage
        """
        self.segments = segments or []
    
    def __iter__(self) -> Iterator[Segment]:
        """Iterate through segments.
        
        Returns
        -------
        Iterator[Segment]
            Iterator over segments
        """
        return iter(self.segments)
    
    def __len__(self) -> int:
        """Get the number of segments.
        
        Returns
        -------
        int
            Number of segments in the manager
        """
        return len(self.segments)
    
    def __getitem__(self, index: int) -> Segment:
        """Get a segment by index.
        
        Parameters
        ----------
        index : int
            Index of the segment to retrieve
            
        Returns
        -------
        Segment
            Segment at the specified index
        """
        return self.segments[index]
    
    def add(self, segment: Segment) -> None:
        """Add a segment to the manager.
        
        Parameters
        ----------
        segment : Segment
            Segment to add
        """
        self.segments.append(segment)
    
    def clear(self) -> None:
        """Clear all segments from the manager."""
        self.segments.clear()
    
    def process_segments(self, processor_func: Callable[[Segment], Any]) -> List[Any]:
        """Process all segments with a given function.
        
        Parameters
        ----------
        processor_func : Callable[[Segment], Any]
            Function to apply to each segment
            
        Returns
        -------
        List[Any]
            List of results from processing each segment
        """
        return [processor_func(segment) for segment in self.segments]
    
    def get_total_tokens(self) -> int:
        """Get the total token count across all segments.
        
        Returns
        -------
        int
            Total number of tokens
        """
        return sum(segment.token_count for segment in self.segments)
    
    def get_average_tokens_per_segment(self) -> float:
        """Get the average token count per segment.
        
        Returns
        -------
        float
            Average token count
        """
        if not self.segments:
            return 0.0
        return self.get_total_tokens() / len(self.segments)
    
    def get_segment_by_id(self, segment_id: int) -> Optional[Segment]:
        """Get a segment by its ID.
        
        Parameters
        ----------
        segment_id : int
            ID of the segment to retrieve
            
        Returns
        -------
        Optional[Segment]
            Segment with the specified ID, or None if not found
        """
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        return None
    
    def get_segment_stats(self) -> Dict[str, Any]:
        """Get statistics about the segments.
        
        Returns
        -------
        Dict[str, Any]
            Dictionary containing segment statistics
        """
        if not self.segments:
            return {
                "total_segments": 0,
                "total_tokens": 0,
                "average_tokens": 0,
                "average_length": 0,
                "total_overlap": 0
            }
        
        total_chars = sum(len(segment.text) for segment in self.segments)
        total_overlap = sum(segment.overlap_before + segment.overlap_after for segment in self.segments)
        
        return {
            "total_segments": len(self.segments),
            "total_tokens": self.get_total_tokens(),
            "average_tokens": self.get_average_tokens_per_segment(),
            "average_length": total_chars / len(self.segments),
            "total_overlap": total_overlap
        }


# ---------------------------------------------------------------------------
# Main Segmenter Implementation
# ---------------------------------------------------------------------------

class TranscriptSegmenter:
    """Service for breaking long transcripts into manageable segments.
    
    This class provides functionality to split long transcript text into 
    smaller segments that respect token limits for AI processing while
    maintaining context and coherence between segments.
    """
    
    # Natural boundary patterns in descending order of preference
    PARAGRAPH_BOUNDARY = r"\n\s*\n"
    SENTENCE_BOUNDARY = r"(?<=[.!?。！？])\s*"
    CLAUSE_BOUNDARY = r"(?<=[,;:，；：])\s*"
    WORD_BOUNDARY = r"\s+"
    
    def __init__(
        self,
        tokenizer: Optional[TokenizerInterface] = None,
        max_tokens_per_segment: int = 2000,
        overlap_strategy: str = "sentence",
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the transcript segmenter.
        
        Parameters
        ----------
        tokenizer : TokenizerInterface, optional
            Tokenizer to use for counting tokens, defaults to SimpleTokenizer
        max_tokens_per_segment : int, default 2000
            Maximum number of tokens per segment
        overlap_strategy : str, default "sentence"
            Strategy for creating overlaps between segments 
            ("none", "sentence", "paragraph", "fixed")
        logger : logging.Logger, optional
            Logger for recording information
        """
        self.tokenizer = tokenizer or SimpleTokenizer()
        self.max_tokens = max_tokens_per_segment
        self.overlap_strategy = overlap_strategy
        self.logger = logger or logging.getLogger(__name__)
    
    def segment_transcript(
        self,
        transcript: str,
        overlap_size: int = 100
    ) -> SegmentManager:
        """Segment a transcript into manageable chunks.
        
        Parameters
        ----------
        transcript : str
            The full transcript text to segment
        overlap_size : int, default 100
            Number of characters to overlap between segments 
            (when using fixed overlap strategy)
            
        Returns
        -------
        SegmentManager
            Manager containing all segments
        """
        if not transcript:
            return SegmentManager([])
        
        # First attempt to split by paragraphs (natural boundaries)
        chunks = self._split_by_natural_boundaries(transcript)
        
        # Then ensure each chunk fits within token limits
        segments = []
        current_pos = 0
        
        for i, chunk in enumerate(chunks):
            # If chunk is too large, split further
            if self.tokenizer.count_tokens(chunk) > self.max_tokens:
                sub_segments = self._split_chunk_to_fit_tokens(
                    chunk, 
                    start_pos=current_pos,
                    base_index=len(segments) + 1
                )
                segments.extend(sub_segments)
            else:
                # Add chunk as a segment directly
                segment = Segment(
                    text=chunk,
                    segment_id=len(segments) + 1,
                    total_segments=0,  # Will update later
                    start_pos=current_pos,
                    end_pos=current_pos + len(chunk),
                    token_count=self.tokenizer.count_tokens(chunk)
                )
                segments.append(segment)
            
            current_pos += len(chunk)
        
        # Update total_segments in all segments
        for segment in segments:
            segment.total_segments = len(segments)
        
        # Add overlaps between segments
        self._add_segment_overlaps(segments, transcript, overlap_size)
        
        return SegmentManager(segments)
    
    def _split_by_natural_boundaries(self, text: str) -> List[str]:
        """Split text at natural boundaries.
        
        Parameters
        ----------
        text : str
            Text to split
            
        Returns
        -------
        List[str]
            List of text chunks split at natural boundaries
        """
        # Try to split by paragraphs first
        chunks = re.split(self.PARAGRAPH_BOUNDARY, text)
        
        # If we only have one chunk or very few, try sentences
        if len(chunks) <= 1:
            chunks = re.split(self.SENTENCE_BOUNDARY, text)
            # Remove empty chunks
            chunks = [c for c in chunks if c.strip()]
        
        # If still just one chunk, return it as is (will handle later)
        if not chunks:
            return [text]
        
        return chunks
    
    def _split_chunk_to_fit_tokens(
        self,
        chunk: str,
        start_pos: int,
        base_index: int
    ) -> List[Segment]:
        """Split a chunk further to fit within token limits.
        
        Parameters
        ----------
        chunk : str
            Text chunk to split
        start_pos : int
            Starting position of the chunk in the original text
        base_index : int
            Base segment ID to start from
            
        Returns
        -------
        List[Segment]
            List of segments that fit within token limits
        """
        segments = []
        current_text = ""
        current_start = start_pos
        current_tokens = 0
        
        # Try to split by sentences first
        sentences = re.split(self.SENTENCE_BOUNDARY, chunk)
        
        # If no sentence breaks, fall back to clauses
        if len(sentences) <= 1:
            sentences = re.split(self.CLAUSE_BOUNDARY, chunk)
        
        # If still no breaks, split by words
        if len(sentences) <= 1:
            sentences = re.split(self.WORD_BOUNDARY, chunk)
        
        # Remove empty sentences
        sentences = [s for s in sentences if s.strip()]
        
        # If nothing to split, return the chunk as one segment
        if not sentences:
            token_count = self.tokenizer.count_tokens(chunk)
            
            # 如果文本的token数小于等于最大限制，直接返回单个段落
            if token_count <= self.max_tokens:
                return [Segment(
                    text=chunk,
                    segment_id=base_index,
                    total_segments=1,  # Temporary, will update later
                    start_pos=start_pos,
                    end_pos=start_pos + len(chunk),
                    token_count=token_count
                )]
            
            # 文本超过token限制，需要强制分割
            # 估算每个token的平均字符数
            chars_per_token = len(chunk) / token_count if token_count > 0 else 2
            
            # 计算每个分段的最大字符数
            max_chars_per_segment = int(self.max_tokens * chars_per_token * 0.9)  # 留出10%的余量
            
            # 强制分割文本
            forced_segments = []
            for i in range(0, len(chunk), max_chars_per_segment):
                segment_text = chunk[i:i+max_chars_per_segment]
                segment_token_count = self.tokenizer.count_tokens(segment_text)
                
                forced_segments.append(Segment(
                    text=segment_text,
                    segment_id=base_index + len(forced_segments),
                    total_segments=0,  # Will update later
                    start_pos=start_pos + i,
                    end_pos=start_pos + i + len(segment_text),
                    token_count=segment_token_count
                ))
            
            return forced_segments
        
        for sentence in sentences:
            sentence_tokens = self.tokenizer.count_tokens(sentence)
            
            # If a single sentence exceeds max tokens, truncate it
            if sentence_tokens > self.max_tokens:
                # Create a segment with the current accumulated text if any
                if current_text:
                    segments.append(Segment(
                        text=current_text,
                        segment_id=base_index + len(segments),
                        total_segments=0,  # Will update later
                        start_pos=current_start,
                        end_pos=current_start + len(current_text),
                        token_count=current_tokens
                    ))
                
                # Truncate the excessive sentence to fit
                truncated_text = self.tokenizer.truncate_text_to_tokens(
                    sentence, self.max_tokens
                )
                
                segments.append(Segment(
                    text=truncated_text,
                    segment_id=base_index + len(segments),
                    total_segments=0,  # Will update later
                    start_pos=start_pos + chunk.find(sentence),
                    end_pos=start_pos + chunk.find(sentence) + len(truncated_text),
                    token_count=self.tokenizer.count_tokens(truncated_text)
                ))
                
                # Reset for next segment
                current_text = ""
                current_tokens = 0
                current_start = start_pos + chunk.find(sentence) + len(sentence)
                continue
            
            # Check if adding the sentence would exceed the token limit
            if current_tokens + sentence_tokens > self.max_tokens and current_text:
                # Create a segment with the current accumulated text
                segments.append(Segment(
                    text=current_text,
                    segment_id=base_index + len(segments),
                    total_segments=0,  # Will update later
                    start_pos=current_start,
                    end_pos=current_start + len(current_text),
                    token_count=current_tokens
                ))
                
                # Reset for next segment
                current_text = sentence
                current_tokens = sentence_tokens
                current_start = start_pos + chunk.find(sentence)
            else:
                # Add the sentence to the current text
                if current_text:
                    current_text += " " + sentence
                else:
                    current_text = sentence
                current_tokens += sentence_tokens
        
        # Add any remaining text as a segment
        if current_text:
            segments.append(Segment(
                text=current_text,
                segment_id=base_index + len(segments),
                total_segments=0,  # Will update later
                start_pos=current_start,
                end_pos=current_start + len(current_text),
                token_count=current_tokens
            ))
        
        return segments
    
    def _add_segment_overlaps(
        self, 
        segments: List[Segment], 
        full_text: str,
        overlap_size: int
    ) -> None:
        """Add overlaps between segments to maintain context.
        
        Parameters
        ----------
        segments : List[Segment]
            List of segments to add overlaps to
        full_text : str
            The original full text
        overlap_size : int
            Size of overlap in characters for fixed strategy
        """
        if not segments or len(segments) < 2:
            return
        
        if self.overlap_strategy == "none":
            return
        
        if self.overlap_strategy == "fixed":
            self._add_fixed_overlaps(segments, full_text, overlap_size)
        elif self.overlap_strategy == "sentence":
            self._add_sentence_overlaps(segments, full_text)
        elif self.overlap_strategy == "paragraph":
            self._add_paragraph_overlaps(segments, full_text)
        else:
            # Default to sentence overlaps
            self._add_sentence_overlaps(segments, full_text)
    
    def _add_fixed_overlaps(
        self, 
        segments: List[Segment], 
        full_text: str,
        overlap_size: int
    ) -> None:
        """Add fixed-size overlaps between segments.
        
        Parameters
        ----------
        segments : List[Segment]
            List of segments to add overlaps to
        full_text : str
            The original full text
        overlap_size : int
            Number of characters to overlap
        """
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]
            
            # Extract overlap from end of current segment
            overlap_text = current_segment.text[-overlap_size:] if len(current_segment.text) > overlap_size else current_segment.text
            
            # Add overlap to beginning of next segment
            if not next_segment.text.startswith(overlap_text):
                next_segment.text = overlap_text + next_segment.text
                next_segment.overlap_before = len(overlap_text)
                next_segment.start_pos -= len(overlap_text)
            
            # Update token count
            next_segment.token_count = self.tokenizer.count_tokens(next_segment.text)
    
    def _add_sentence_overlaps(self, segments: List[Segment], full_text: str) -> None:
        """Add sentence-based overlaps between segments.
        
        Parameters
        ----------
        segments : List[Segment]
            List of segments to add overlaps to
        full_text : str
            The original full text
        """
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]
            
            # Find the last complete sentence in the current segment
            last_sentence_match = list(re.finditer(r"[^.!?]+[.!?]", current_segment.text))
            
            if last_sentence_match:
                last_sentence = last_sentence_match[-1].group(0)
                
                # Add the last sentence as overlap to the next segment
                if not next_segment.text.startswith(last_sentence):
                    next_segment.text = last_sentence + " " + next_segment.text
                    next_segment.overlap_before = len(last_sentence) + 1
                    next_segment.start_pos -= len(last_sentence) + 1
                
                # Update token count
                next_segment.token_count = self.tokenizer.count_tokens(next_segment.text)
    
    def _add_paragraph_overlaps(self, segments: List[Segment], full_text: str) -> None:
        """Add paragraph-based overlaps between segments.
        
        Parameters
        ----------
        segments : List[Segment]
            List of segments to add overlaps to
        full_text : str
            The original full text
        """
        for i in range(len(segments) - 1):
            current_segment = segments[i]
            next_segment = segments[i + 1]
            
            # Find paragraphs by looking for double newlines
            paragraphs = re.split(r"\n\s*\n", current_segment.text)
            
            if len(paragraphs) > 1:
                last_paragraph = paragraphs[-1]
                
                # Add the last paragraph as overlap to the next segment
                if not next_segment.text.startswith(last_paragraph):
                    next_segment.text = last_paragraph + "\n\n" + next_segment.text
                    next_segment.overlap_before = len(last_paragraph) + 2
                    next_segment.start_pos -= len(last_paragraph) + 2
                
                # Update token count
                next_segment.token_count = self.tokenizer.count_tokens(next_segment.text)
            else:
                # Fall back to sentence overlap if no paragraphs found
                self._add_sentence_overlaps([current_segment, next_segment], full_text) 