from __future__ import annotations

"""Summarizer service for article generation.

Implements *task 4.5 (Create core SummarizerService class)* by providing a 
service that processes transcript segments and generates Medium-style articles
using the DeepSeek API.

Key components:
- SummarizerService - Main service for transforming transcripts into articles
- SummarizerConfig - Configuration for the summarizer service
- SummarizerResult - Results from a summarization process

This service coordinates between:
1. Transcript segmentation (TranscriptSegmenter)
2. Prompt creation (PromptAssembler)  
3. LLM interaction (DeepSeekService)
"""

import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.models.template import Template
from src.services.deepseek_service import DeepSeekService, DeepSeekError
from src.services.prompt_templates import PromptAssembler
from src.services.transcript_segmenter import TranscriptSegmenter, SegmentManager, Segment


class SummarizationStatus(Enum):
    """Status of a summarization process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationMetrics:
    """Metrics about the generation process."""
    total_tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generation_time_seconds: float = 0
    segment_count: int = 0
    average_tokens_per_segment: float = 0
    segment_processing_times: List[float] = field(default_factory=list)


@dataclass
class SummarizerConfig:
    """Configuration for the summarizer service."""
    model: str = "deepseek-chat-6.7b"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Segments configuration
    max_tokens_per_segment: int = 4000
    overlap_strategy: str = "sentence"
    overlap_size: int = 150
    

@dataclass
class SummarizerResult:
    """Results from a summarization process."""
    article_text: str
    title: str 
    status: SummarizationStatus
    metrics: GenerationMetrics
    template_id: str
    segments_used: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SummarizerService:
    """Service for generating summarized content from transcripts.
    
    This service handles the process of breaking down long transcripts into
    manageable segments, generating content for each segment using the DeepSeek API,
    and combining the results into a coherent article.
    """
    
    def __init__(
        self,
        deepseek_service: DeepSeekService,
        prompt_assembler: Optional[PromptAssembler] = None,
        segmenter: Optional[TranscriptSegmenter] = None,
        config: Optional[SummarizerConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the summarizer service.
        
        Parameters
        ----------
        deepseek_service : DeepSeekService
            Service for interacting with DeepSeek API
        prompt_assembler : PromptAssembler, optional
            Service for assembling prompts
        segmenter : TranscriptSegmenter, optional
            Service for segmenting transcripts
        config : SummarizerConfig, optional
            Configuration for the summarizer
        logger : logging.Logger, optional
            Logger for the service
        """
        self.deepseek_service = deepseek_service
        self.prompt_assembler = prompt_assembler or PromptAssembler()
        self.segmenter = segmenter or TranscriptSegmenter()
        self.config = config or SummarizerConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Track active jobs for cancellation support
        self._cancellation_flags: Dict[str, bool] = {}
        self._lock = threading.RLock()  # Add a lock for thread safety
    
    def is_job_cancelled(self, job_id: Optional[str]) -> bool:
        """Check if a job is marked for cancellation.
        
        Parameters
        ----------
        job_id : str, optional
            The ID of the job to check
            
        Returns
        -------
        bool
            True if job is marked for cancellation, False otherwise
        """
        if not job_id:
            return False
            
        with self._lock:  # Use lock for thread safety
            return self._cancellation_flags.get(job_id, False)
    
    def generate_article(
        self, 
        transcript: str, 
        template: Template,
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        extra_instructions: Optional[str] = None,
    ) -> SummarizerResult:
        """Generate an article from a transcript.
        
        Parameters
        ----------
        transcript : str
            The transcript text to summarize
        template : Template
            The template to use for generation
        job_id : str, optional
            Identifier for the job, used for cancellation
        progress_callback : Callable[[float, str], None], optional
            Callback for reporting progress (0.0-1.0, status message)
        extra_instructions : str, optional
            Additional instructions for the model
            
        Returns
        -------
        SummarizerResult
            The generated article and metadata
        """
        # Initialize metrics
        metrics = GenerationMetrics()
        start_time = time.time()
        
        # Register job for cancellation if ID provided
        if job_id:
            with self._lock:  # Use lock for thread safety
                self._cancellation_flags[job_id] = False
        
        try:
            # Segment the transcript
            if progress_callback:
                progress_callback(0.1, "Segmenting transcript...")
            
            segment_manager = self.segmenter.segment_transcript(
                transcript,
                max_tokens_per_segment=self.config.max_tokens_per_segment,
                overlap_strategy=self.config.overlap_strategy,
                overlap_size=self.config.overlap_size
            )
            
            metrics.segment_count = len(segment_manager)
            
            if not segment_manager or len(segment_manager) == 0:
                raise ValueError("Failed to segment transcript or empty transcript provided")
            
            # Check for cancellation
            if self.is_job_cancelled(job_id):
                return SummarizerResult(
                    article_text="",
                    title="",
                    status=SummarizationStatus.CANCELLED,
                    metrics=metrics,
                    template_id=template.id,
                    segments_used=0,
                    error_message="Generation cancelled by user"
                )
            
            # Process each segment
            segment_results = self._process_segments(
                segment_manager, 
                template, 
                job_id, 
                progress_callback,
                extra_instructions
            )
            
            # If we have some results but job was cancelled, combine the partial results
            if segment_results and self.is_job_cancelled(job_id):
                partial_article_text, partial_title = self._combine_segments(segment_results)
                return SummarizerResult(
                    article_text=partial_article_text,
                    title=partial_title,
                    status=SummarizationStatus.CANCELLED,
                    metrics=metrics,
                    template_id=template.id,
                    segments_used=len(segment_results),
                    error_message="Generation cancelled by user (partial results returned)"
                )
            
            # Combine the segments
            if progress_callback:
                progress_callback(0.9, "Combining segments...")
            
            article_text, title = self._combine_segments(segment_results)
            
            # Calculate final metrics
            metrics.generation_time_seconds = time.time() - start_time
            if metrics.segment_count > 0:
                metrics.average_tokens_per_segment = metrics.total_tokens_used / metrics.segment_count
            
            return SummarizerResult(
                article_text=article_text,
                title=title,
                status=SummarizationStatus.COMPLETED,
                metrics=metrics,
                template_id=template.id,
                segments_used=len(segment_manager)
            )
            
        except DeepSeekError as e:
            self.logger.error(f"DeepSeek API error: {str(e)}")
            return SummarizerResult(
                article_text="",
                title="",
                status=SummarizationStatus.FAILED,
                metrics=metrics,
                template_id=template.id,
                segments_used=0,
                error_message=f"DeepSeek API error: {str(e)}"
            )
        except RuntimeError as e:
            # Special handling for cancellation during segment processing
            if "Job cancelled" in str(e):
                self.logger.info(f"Job {job_id} cancelled during processing: {str(e)}")
                return SummarizerResult(
                    article_text="",
                    title="",
                    status=SummarizationStatus.CANCELLED,
                    metrics=metrics,
                    template_id=template.id,
                    segments_used=0,
                    error_message=f"Generation cancelled: {str(e)}"
                )
            # Regular error handling
            self.logger.exception("Summarization failed")
            return SummarizerResult(
                article_text="",
                title="",
                status=SummarizationStatus.FAILED,
                metrics=metrics,
                template_id=template.id,
                segments_used=0,
                error_message=str(e)
            )
        except Exception as e:
            self.logger.exception("Summarization failed")
            return SummarizerResult(
                article_text="",
                title="",
                status=SummarizationStatus.FAILED,
                metrics=metrics,
                template_id=template.id,
                segments_used=0,
                error_message=str(e)
            )
        finally:
            # Clean up cancellation flag
            if job_id:
                with self._lock:  # Use lock for thread safety
                    if job_id in self._cancellation_flags:
                        del self._cancellation_flags[job_id]
    
    def _process_segments(
        self,
        segment_manager: SegmentManager,
        template: Template,
        job_id: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]],
        extra_instructions: Optional[str]
    ) -> List[Tuple[str, str]]:
        """Process each segment to generate content.
        
        Parameters
        ----------
        segment_manager : SegmentManager
            Manager containing all segments
        template : Template
            The template to use for generation
        job_id : str, optional
            Identifier for the job, used for cancellation
        progress_callback : Callable[[float, str], None], optional
            Callback for reporting progress
        extra_instructions : str, optional
            Additional instructions for the model
            
        Returns
        -------
        List[Tuple[str, str]]
            List of (content, title) tuples for each segment
        """
        results = []
        title = ""
        segment_count = len(segment_manager)
        
        for i, segment in enumerate(segment_manager):
            # Check for cancellation
            if self.is_job_cancelled(job_id):
                self.logger.info(f"Job {job_id} cancelled during segment processing")
                break
            
            # Update progress
            progress_percent = 0.1 + 0.8 * (i / max(1, segment_count))
            if progress_callback:
                progress_callback(
                    progress_percent, 
                    f"Processing segment {i+1}/{segment_count}..."
                )
            
            # Set special parameters for first and last segments
            segment_instructions = extra_instructions or ""
            if segment.is_first:
                segment_instructions += "\nThis is the first segment. Include a compelling title and introduction."
            
            if segment.is_last:
                segment_instructions += "\nThis is the last segment. Include a conclusive ending."
                
            # Add overlap context for non-first segments
            context = ""
            if not segment.is_first and segment.overlap_before > 0:
                # Extract the overlap text from the beginning of this segment
                overlap_text = segment.text[:segment.overlap_before]
                context = f"\nContext from previous segment: {overlap_text}"
                
            # Process with retries
            try:
                content, segment_title, tokens_used = self._process_single_segment(
                    segment, 
                    template, 
                    segment_instructions, 
                    context,
                    job_id  # Pass job_id to check for cancellation
                )
                
                # Save the title from the first segment
                if segment.is_first and segment_title:
                    title = segment_title
                
                # Store result
                results.append((content, segment_title))
                
                # Record segment processing time and token usage
                segment_process_time = time.time()
                self.logger.info(f"Segment {i+1}/{segment_count} processed: {tokens_used} tokens used")
            except Exception as e:
                # If this was a cancellation, we want to preserve any results so far
                if "Job cancelled" in str(e):
                    self.logger.info(f"Job {job_id} cancelled while processing segment {i+1}: {str(e)}")
                    break
                # For other errors, re-raise
                raise
        
        return results
    
    def _process_single_segment(
        self, 
        segment: Segment, 
        template: Template,
        extra_instructions: str,
        context: str,
        job_id: Optional[str] = None  # Add job_id parameter
    ) -> Tuple[str, str, int]:
        """Process a single segment with retries.
        
        Parameters
        ----------
        segment : Segment
            The segment to process
        template : Template
            The template to use
        extra_instructions : str
            Additional instructions
        context : str
            Context from previous segments
        job_id : str, optional
            Identifier for cancellation checks
            
        Returns
        -------
        Tuple[str, str, int]
            (content, title, tokens_used)
        """
        combined_instructions = f"{extra_instructions}\n{context}".strip()
        
        for attempt in range(self.config.max_retries):
            try:
                # Check for cancellation before making API call
                if self.is_job_cancelled(job_id):
                    raise RuntimeError("Job cancelled during segment processing")
                    
                # Build the prompt for this segment
                prompt = self.prompt_assembler.build_prompt(
                    template=template,
                    transcript_segment=segment.text,
                    extra_instructions=combined_instructions if combined_instructions else None
                )
                
                # Make the API call
                segment_start_time = time.time()
                
                # TODO: Add support for timeouts and cancellation during API calls
                # This would require modifying DeepSeekService to support timeouts
                # and checking cancellation periodically during long API calls
                
                response = self.deepseek_service.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are an article writer that transforms video transcripts into engaging Medium-style content."},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    top_p=self.config.top_p
                )
                
                # Extract the title if present
                content = response
                title = ""
                
                # Check for title in the format "# Title" or "Title:"
                if content.startswith("# "):
                    title_end = content.find("\n")
                    if title_end > 2:
                        title = content[2:title_end].strip()
                elif ":" in content[:50]:
                    title_end = content.find("\n")
                    if title_end > 0:
                        potential_title = content[:title_end].strip()
                        if len(potential_title) < 100:  # Reasonable title length
                            title = potential_title
                
                # Calculate tokens - simplified estimate for now
                # In a real implementation, you would get exact counts from the API response
                tokens_used = len(prompt.split()) + len(content.split())
                
                return content, title, tokens_used
                
            except DeepSeekError as e:
                # Check for cancellation before retrying
                if self.is_job_cancelled(job_id):
                    raise RuntimeError("Job cancelled during retry delay")
                    
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"DeepSeek API error, retrying: {str(e)}")
                    time.sleep(self.config.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise
            except RuntimeError as e:
                # Re-raise cancellation errors
                if "Job cancelled" in str(e):
                    raise
                # For other runtime errors, re-raise with more context
                raise RuntimeError(f"Failed to process segment: {str(e)}")
        
        # This should never be reached due to the exception in the loop
        raise RuntimeError("Failed to process segment after all retries")
    
    def _combine_segments(self, segment_results: List[Tuple[str, str]]) -> Tuple[str, str]:
        """Combine segment results into a complete article.
        
        Parameters
        ----------
        segment_results : List[Tuple[str, str]]
            List of (content, title) tuples for each segment
            
        Returns
        -------
        Tuple[str, str]
            (full_article, title)
        """
        if not segment_results:
            return "", ""
        
        # Use the title from the first segment
        title = segment_results[0][1]
        
        # Combine the content, removing duplicate titles
        combined_content = []
        
        for i, (content, segment_title) in enumerate(segment_results):
            # Skip the title line in non-first segments
            if i > 0 and content.startswith("# "):
                content = content[content.find("\n")+1:]
            
            combined_content.append(content)
        
        return "\n\n".join(combined_content), title
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel an in-progress summarization job.
        
        Parameters
        ----------
        job_id : str
            The ID of the job to cancel
            
        Returns
        -------
        bool
            True if job was found and marked for cancellation, False otherwise
        """
        with self._lock:  # Use lock for thread safety
            if job_id in self._cancellation_flags:
                self._cancellation_flags[job_id] = True
                self.logger.info(f"Job {job_id} marked for cancellation")
                return True
            return False 