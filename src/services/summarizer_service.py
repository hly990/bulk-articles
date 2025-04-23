from __future__ import annotations

"""Summarizer service for article generation.

Implements *task 4.5 (Create core SummarizerService class)* by providing a 
service that processes transcript segments and generates Medium-style articles
using the DeepSeek API.

Key components:
- SummarizerService - Main service for transforming transcripts into articles
- SummarizerConfig - Configuration for the summarizer service
- SummarizerResult - Results from a summarization process

Updates in task 4.7:
- Added token usage tracking and optimization
- Added adaptive prompt sizing based on token limits
- Added budget control and token usage estimation

This service coordinates between:
1. Transcript segmentation (TranscriptSegmenter)
2. Prompt creation (PromptAssembler)  
3. LLM interaction (DeepSeekService)
4. Token usage tracking (TokenUsageTracker)
"""

import logging
import time
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.models.template import Template
from src.services.deepseek_service import DeepSeekService, DeepSeekError
from src.services.prompt_templates import PromptAssembler
from src.services.transcript_segmenter import TranscriptSegmenter, SegmentManager, Segment

# Import token tracker, but make it optional
try:
    from src.services.token_usage_tracker import TokenUsageTracker, TokenOptimizer, TokenBudgetExceededError
except ImportError:
    TokenUsageTracker = None  # type: ignore
    TokenOptimizer = None  # type: ignore
    TokenBudgetExceededError = Exception  # type: ignore


class SummarizationStatus(Enum):
    """Status of a summarization process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXCEEDED = "budget_exceeded"


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
    token_usage_by_segment: List[Dict[str, int]] = field(default_factory=list)
    token_savings_from_optimization: int = 0
    estimated_cost: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary for serialization."""
        return {
            "total_tokens_used": self.total_tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "generation_time_seconds": round(self.generation_time_seconds, 2),
            "segment_count": self.segment_count,
            "average_tokens_per_segment": round(self.average_tokens_per_segment, 2),
            "segment_processing_times": [round(t, 2) for t in self.segment_processing_times],
            "token_usage_by_segment": self.token_usage_by_segment,
            "token_savings_from_optimization": self.token_savings_from_optimization,
            "estimated_cost": round(self.estimated_cost, 4)
        }
    
    def calculate_average_tokens_per_segment(self) -> None:
        """Calculate average tokens per segment."""
        if self.segment_count > 0:
            self.average_tokens_per_segment = self.total_tokens_used / self.segment_count


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
    
    # Token optimization configuration
    optimize_prompts: bool = True
    adaptive_token_limits: bool = True
    max_prompt_tokens_per_request: int = 12000
    safety_margin: float = 0.9  # Percentage of max tokens to use (safety margin)
    

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a dictionary for serialization."""
        return {
            "article_text": self.article_text,
            "title": self.title,
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "template_id": self.template_id,
            "segments_used": self.segments_used,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


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
        token_tracker: Optional[TokenUsageTracker] = None,
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
        token_tracker : TokenUsageTracker, optional
            Service for tracking token usage
        """
        self.deepseek_service = deepseek_service
        self.prompt_assembler = prompt_assembler or PromptAssembler()
        self.segmenter = segmenter or TranscriptSegmenter()
        self.config = config or SummarizerConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.token_tracker = token_tracker
        
        # Check if deepseek_service already has a token_tracker, and if so, use that one
        if token_tracker is None and hasattr(deepseek_service, 'token_tracker') and deepseek_service.token_tracker:
            self.token_tracker = deepseek_service.token_tracker
            self.logger.debug("Using token tracker from DeepSeekService")
        
        # Track active jobs for cancellation support
        self._cancellation_flags: Dict[str, bool] = {}
        self._lock = threading.RLock()  # Add a lock for thread safety
        
        # Log configuration
        self.logger.info(
            "SummarizerService initialized with model=%s, token_tracker=%s, optimize_prompts=%s",
            self.config.model,
            "enabled" if self.token_tracker else "disabled",
            self.config.optimize_prompts
        )
    
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
        # Generate a job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
            
        # Initialize metrics
        metrics = GenerationMetrics()
        start_time = time.time()
        
        # Register job for cancellation if ID provided
        with self._lock:  # Use lock for thread safety
            self._cancellation_flags[job_id] = False
        
        # Estimate token usage before processing
        if self.token_tracker:
            try:
                estimated_tokens = self._estimate_total_tokens(transcript, template, extra_instructions)
                self.logger.info(f"Estimated total tokens for job {job_id}: {estimated_tokens:,}")
                
                # Log estimation in metrics
                metrics.metadata = metrics.metadata or {}
                metrics.metadata["estimated_tokens"] = estimated_tokens
                
                # Check if we might exceed budget
                if self.token_tracker:
                    # This is just an estimate check, not actual tracking
                    remaining_tokens = self.token_tracker.get_remaining_tokens()
                    remaining_budget = self.token_tracker.get_remaining_budget()
                    
                    if remaining_tokens != float('inf') and estimated_tokens > remaining_tokens:
                        self.logger.warning(
                            f"Estimated tokens ({estimated_tokens:,}) exceeds remaining token budget "
                            f"({remaining_tokens:,}). Proceeding anyway, but may fail during processing."
                        )
                
            except Exception as e:
                self.logger.warning(f"Failed to estimate token usage: {e}")
        
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
                    template_id=template.template_id,
                    segments_used=0,
                    error_message="Job cancelled before processing segments"
                )
            
            # Process segments
            if progress_callback:
                progress_callback(0.2, f"Processing {len(segment_manager)} segments...")
                
            try:
                segment_results = self._process_segments(segment_manager, template, job_id, progress_callback, extra_instructions)
            except TokenBudgetExceededError as e:
                # Handle budget exceeded error
                return SummarizerResult(
                    article_text="",
                    title="",
                    status=SummarizationStatus.BUDGET_EXCEEDED,
                    metrics=metrics,
                    template_id=template.template_id,
                    segments_used=0,
                    error_message=f"Token budget exceeded: {e}"
                )
                
            # Check for cancellation
            if self.is_job_cancelled(job_id):
                return SummarizerResult(
                    article_text="",
                    title="",
                    status=SummarizationStatus.CANCELLED,
                    metrics=metrics,
                    template_id=template.template_id,
                    segments_used=len(segment_results),
                    error_message="Job cancelled after processing segments"
                )
            
            # Combine segment results
            if progress_callback:
                progress_callback(0.8, "Combining segments...")
                
            article_text, title = self._combine_segments(segment_results)
            
            # Complete metrics
            metrics.generation_time_seconds = time.time() - start_time
            metrics.calculate_average_tokens_per_segment()
            
            # Add estimated cost from token tracker if available
            if self.token_tracker:
                # This is just a rough estimation based on the tracked usage for this job
                metrics.estimated_cost = sum([
                    usage.get("estimated_cost", 0.0) 
                    for usage in metrics.token_usage_by_segment
                ])
            
            if progress_callback:
                progress_callback(1.0, "Article generation complete")
                
            # Return the result
            return SummarizerResult(
                article_text=article_text,
                title=title,
                status=SummarizationStatus.COMPLETED,
                metrics=metrics,
                template_id=template.template_id,
                segments_used=len(segment_results),
                metadata={
                    "token_tracking_enabled": self.token_tracker is not None,
                    "prompt_optimization_enabled": self.config.optimize_prompts and TokenOptimizer is not None,
                }
            )
                
        except DeepSeekError as e:
            self.logger.error(f"DeepSeek API error during article generation: {e}")
            return SummarizerResult(
                article_text="",
                title="",
                status=SummarizationStatus.FAILED,
                metrics=metrics,
                template_id=template.template_id,
                segments_used=0,
                error_message=f"DeepSeek API error: {e}"
            )
        except Exception as e:
            self.logger.exception(f"Error during article generation: {e}")
            return SummarizerResult(
                article_text="",
                title="",
                status=SummarizationStatus.FAILED,
                metrics=metrics,
                template_id=template.template_id,
                segments_used=0,
                error_message=f"Error during generation: {e}"
            )
        finally:
            # Clean up cancellation flag
            with self._lock:
                self._cancellation_flags.pop(job_id, None)
    
    def _process_segments(
        self,
        segment_manager: SegmentManager,
        template: Template,
        job_id: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]],
        extra_instructions: Optional[str]
    ) -> List[Tuple[str, str]]:
        """Process transcript segments to generate content.
        
        Parameters
        ----------
        segment_manager : SegmentManager
            Manager containing transcript segments
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
        segment_count = len(segment_manager)
        
        # Build initial context from first segment
        context = ""
        
        # Process each segment
        for i, segment in enumerate(segment_manager):
            # Check for cancellation before processing segment
            if self.is_job_cancelled(job_id):
                self.logger.info(f"Job {job_id} cancelled during segment processing")
                break
                
            # Update progress
            progress_percentage = 0.2 + (0.6 * (i / segment_count))
            if progress_callback:
                progress_callback(
                    progress_percentage,
                    f"Processing segment {i+1}/{segment_count}..."
                )
                
            # Add extra line of logging for token tracking
            if self.token_tracker:
                self.logger.info(
                    f"Processing segment {i+1}/{segment_count} - remaining budget: "
                    f"${self.token_tracker.get_remaining_budget():.2f}, "
                    f"remaining tokens: {self.token_tracker.get_remaining_tokens():,}"
                )
            
            # Get extra instructions for this segment (if any)
            segment_instructions = extra_instructions or ""
            
            try:
                # Process the segment with retries
                content, title, usage = self._process_single_segment(
                    segment,
                    template,
                    segment_instructions,
                    context,
                    job_id
                )
                
                # Add the result and update context for next segment
                results.append((content, title))
                
                # Use the generated content as context for the next segment
                # But limit to a reasonable size to avoid token explosion
                context = content[-1000:] if content else ""
                
            except Exception as e:
                self.logger.error(f"Error processing segment {i+1}: {e}")
                # Continue with next segment rather than failing the whole job
                continue
                
        return results
        
    def _process_single_segment(
        self, 
        segment: Segment, 
        template: Template,
        extra_instructions: str,
        context: str,
        job_id: Optional[str] = None
    ) -> Tuple[str, str, Dict[str, int]]:
        """Process a single transcript segment using the DeepSeek API.
        
        Parameters
        ----------
        segment : Segment
            Transcript segment to process
        template : Template
            Template to use for generation
        extra_instructions : str
            Additional instructions for the model
        context : str
            Context from previous segments
        job_id : str, optional
            Identifier for the job
            
        Returns
        -------
        Tuple[str, str, Dict[str, int]]
            Tuple of (content, title, token_usage)
        """
        segment_start_time = time.time()
        retry_count = 0
        segment_id = f"{job_id}_{segment.segment_id}" if job_id else f"segment_{segment.segment_id}"
        
        # Get max tokens for completion
        max_tokens = self.config.max_tokens
        
        # Create the prompt
        prompt = self.prompt_assembler.create_summary_prompt(
            segment.text,
            template,
            is_continuation=(segment.segment_id > 0),
            previous_context=context,
            extra_instructions=extra_instructions
        )
        
        # Optimize the prompt if enabled
        original_prompt_size = None
        optimized_prompt = prompt
        
        if self.config.optimize_prompts and TokenOptimizer and self.token_tracker:
            original_prompt_size = self.token_tracker.estimate_token_count(prompt)
            
            # Apply optimization
            optimized_prompt = TokenOptimizer.optimize_prompt(
                prompt=prompt,
                instructions=extra_instructions or "Summarize this transcript segment into an article"
            )
            
            # Apply token limit if adaptive token limits are enabled
            if self.config.adaptive_token_limits:
                # Get adaptive max prompt tokens based on remaining budget
                adaptive_max_tokens = min(
                    self.config.max_prompt_tokens_per_request,
                    int(self.token_tracker.get_remaining_tokens() * 0.8)  # Use up to 80% of remaining tokens
                )
                
                # Make sure we have a reasonable minimum
                adaptive_max_tokens = max(adaptive_max_tokens, 1000)
                
                # Truncate if needed
                optimized_prompt = TokenOptimizer.truncate_to_token_limit(
                    optimized_prompt, 
                    adaptive_max_tokens, 
                    self.token_tracker
                )
            
            # Log optimization results
            optimized_size = self.token_tracker.estimate_token_count(optimized_prompt)
            savings = max(0, original_prompt_size - optimized_size)
            
            if savings > 0:
                self.logger.info(
                    f"Optimized prompt for segment {segment.segment_id}. "
                    f"Original: ~{original_prompt_size} tokens, "
                    f"Optimized: ~{optimized_size} tokens, "
                    f"Savings: ~{savings} tokens ({savings/original_prompt_size:.1%})"
                )
        
        # Create request ID for tracking
        request_id = segment_id
        
        while retry_count <= self.config.max_retries:
            try:
                # Check for cancellation before API call
                if self.is_job_cancelled(job_id):
                    raise ValueError("Job cancelled during segment processing")
                
                # Call the API with optimized prompt
                response = self.deepseek_service.chat_completion(
                    messages=[
                        {"role": "user", "content": optimized_prompt}
                    ],
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=max_tokens,
                    request_id=request_id,
                    context=f"Segment {segment.segment_id} processing for job {job_id}"
                )
                
                # Parse the response to extract title and content
                title, content = self._parse_response(response)
                
                # Update token usage metrics
                segment_processing_time = time.time() - segment_start_time
                
                # Get token usage from API if available, otherwise use estimates
                token_usage = {}
                
                if hasattr(self.deepseek_service, 'token_tracker') and self.deepseek_service.token_tracker:
                    # Get the latest record for this request
                    stats = self.deepseek_service.token_tracker.get_usage_stats()
                    
                    # Find records matching this request ID
                    matching_records = [
                        r for r in getattr(self.deepseek_service.token_tracker, '_usage_records', [])
                        if getattr(r, 'request_id', '') == request_id
                    ]
                    
                    if matching_records:
                        latest_record = matching_records[-1]
                        token_usage = {
                            "prompt_tokens": latest_record.prompt_tokens,
                            "completion_tokens": latest_record.completion_tokens,
                            "total_tokens": latest_record.total_tokens,
                            "estimated_cost": latest_record.estimated_cost
                        }
                    else:
                        # Fallback to estimation
                        prompt_tokens = self.token_tracker.estimate_token_count(optimized_prompt)
                        completion_tokens = self.token_tracker.estimate_token_count(response)
                        token_usage = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                            "estimated_cost": 0.0001  # Very rough estimate
                        }
                
                # Update metrics
                self.logger.info(
                    f"Segment {segment.segment_id} processed in {segment_processing_time:.2f}s, "
                    f"using ~{token_usage.get('total_tokens', 'unknown')} tokens"
                )
                
                return content, title, token_usage
                
            except TokenBudgetExceededError:
                # Don't retry, just raise the exception
                raise
            
            except Exception as e:
                retry_count += 1
                wait_time = self.config.retry_delay * retry_count
                
                self.logger.warning(
                    f"Error processing segment {segment.segment_id} (attempt {retry_count}/{self.config.max_retries}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                
                # If we've reached max retries, raise the exception
                if retry_count > self.config.max_retries:
                    raise
                    
                # Wait before retrying
                time.sleep(wait_time)
        
        # This should never be reached due to the raises above, but just in case
        raise RuntimeError(f"Failed to process segment {segment.segment_id} after {self.config.max_retries} retries")
    
    def _parse_response(self, response: str) -> Tuple[str, str]:
        """Parse the model response to extract title and content.
        
        Parameters
        ----------
        response : str
            Raw model response
            
        Returns
        -------
        Tuple[str, str]
            Tuple of (title, content)
        """
        lines = response.split('\n')
        
        # Extract title - assume first line that starts with # or Title:
        title = ""
        content_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                content_start = i + 1
                break
            elif line.lower().startswith('title:'):
                title = line[6:].strip()
                content_start = i + 1
                break
                
        # If no title found, use first sentence or first 50 chars
        if not title and lines:
            first_content_line = lines[0].strip()
            title = first_content_line.split('.')[0]
            if len(title) > 50:
                title = title[:47] + "..."
                
        # Get content (everything after title)
        content = '\n'.join(lines[content_start:]).strip()
        
        return title, content
    
    def _combine_segments(self, segment_results: List[Tuple[str, str]]) -> Tuple[str, str]:
        """Combine processed segment results into a single article.
        
        Parameters
        ----------
        segment_results : List[Tuple[str, str]]
            List of (content, title) tuples for each segment
            
        Returns
        -------
        Tuple[str, str]
            Tuple of (article_text, title)
        """
        if not segment_results:
            return "", ""
            
        # Use the title from the first segment
        title = segment_results[0][1]
        
        # Join content from all segments
        content_parts = [result[0] for result in segment_results]
        article_text = "\n\n".join(content_parts)
        
        # Clean up
        article_text = self._clean_combined_article(article_text, title)
        
        return article_text, title
        
    def _clean_combined_article(self, article_text: str, title: str) -> str:
        """Clean up the combined article text.
        
        Parameters
        ----------
        article_text : str
            Raw combined article text
        title : str
            Article title
            
        Returns
        -------
        str
            Cleaned article text
        """
        # Remove duplicate headings, specially if they match the title
        lines = article_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just the title
            if stripped.startswith('# ') and stripped[2:].strip().lower() == title.lower():
                continue
            # Skip lines with "Title:" prefix
            if stripped.lower().startswith('title:'):
                continue
                
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)
    
    def _estimate_total_tokens(
        self, 
        transcript: str, 
        template: Template, 
        extra_instructions: Optional[str]
    ) -> int:
        """Estimate the total tokens for processing a transcript.
        
        Parameters
        ----------
        transcript : str
            Full transcript text
        template : Template
            Template to use for generation
        extra_instructions : str, optional
            Additional instructions
            
        Returns
        -------
        int
            Estimated total tokens
        """
        if not self.token_tracker:
            # Can't estimate without token tracker
            return 0
            
        # Segment the transcript
        segment_manager = self.segmenter.segment_transcript(
            transcript,
            max_tokens_per_segment=self.config.max_tokens_per_segment,
            overlap_strategy=self.config.overlap_strategy,
            overlap_size=self.config.overlap_size
        )
        
        segment_count = len(segment_manager)
        
        # Estimate prompt token usage for a sample segment
        sample_prompt = ""
        if segment_count > 0:
            # Use the first segment as a sample
            sample_prompt = self.prompt_assembler.create_summary_prompt(
                segment_manager[0].text,
                template,
                is_continuation=False,
                extra_instructions=extra_instructions
            )
        
        prompt_tokens = self.token_tracker.estimate_token_count(sample_prompt)
        
        # Estimate completion tokens based on configured max_tokens
        completion_tokens = min(self.config.max_tokens, 2000)  # Use configured max tokens or 2000 as default
        
        # Estimate total
        tokens_per_segment = prompt_tokens + completion_tokens
        total_estimated = tokens_per_segment * segment_count
        
        return total_estimated
        
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.
        
        Parameters
        ----------
        job_id : str
            ID of the job to cancel
            
        Returns
        -------
        bool
            True if job was found and marked for cancellation, False otherwise
        """
        with self._lock:
            if job_id in self._cancellation_flags:
                self._cancellation_flags[job_id] = True
                self.logger.info(f"Job {job_id} marked for cancellation")
                return True
            else:
                self.logger.warning(f"Job {job_id} not found, can't cancel")
                return False
    
    def get_token_usage_stats(self) -> Optional[Dict[str, Any]]:
        """Get token usage statistics if token tracking is enabled.
        
        Returns
        -------
        Dict[str, Any] or None
            Token usage statistics, or None if token tracking is disabled
        """
        if not self.token_tracker:
            return None
            
        stats = self.token_tracker.get_usage_stats()
        return stats.to_dict() if stats else None
    
    def get_remaining_budget(self) -> Dict[str, Any]:
        """Get remaining token budget information.
        
        Returns
        -------
        Dict[str, Any]
            Budget information
        """
        if not self.token_tracker:
            return {
                "token_tracking_enabled": False,
                "remaining_tokens": "unlimited",
                "remaining_budget": "unlimited"
            }
            
        return {
            "token_tracking_enabled": True,
            "remaining_tokens": self.token_tracker.get_remaining_tokens(),
            "remaining_budget": f"${self.token_tracker.get_remaining_budget():.2f}",
            "budget_limit": (
                f"${self.token_tracker.budget_limit:.2f}" 
                if self.token_tracker.budget_limit is not None 
                else "unlimited"
            ),
            "token_limit": (
                f"{self.token_tracker.token_limit:,}" 
                if self.token_tracker.token_limit is not None 
                else "unlimited"
            )
        } 