"""Services package for YT-Article Craft"""

from importlib import metadata

try:
    # Expose wrapper at package level for convenience
    from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError  # noqa: F401
except ModuleNotFoundError:
    # Wrapper may not be available yet during initial installation
    YtDlpWrapper = None  # type: ignore
    YtDlpError = RuntimeError  # type: ignore

# Import caption models
try:
    from .caption_model import Caption, CaptionLine, CaptionMetadata, CaptionError
except ModuleNotFoundError:
    Caption = None  # type: ignore
    CaptionLine = None  # type: ignore
    CaptionMetadata = None  # type: ignore
    CaptionError = RuntimeError  # type: ignore

# Import subtitle parser
try:
    from .subtitle_parser import ParserFactory, ParserError, SrtParser, VttParser
except ModuleNotFoundError:
    ParserFactory = None  # type: ignore
    ParserError = RuntimeError  # type: ignore
    SrtParser = None  # type: ignore
    VttParser = None  # type: ignore

# Import caption service
try:
    from .caption_service import CaptionService
except ModuleNotFoundError:
    CaptionService = None  # type: ignore

# Import caption cache
try:
    from .caption_cache import CaptionCache, CacheConfig, CacheKey
except ModuleNotFoundError:
    CaptionCache = None  # type: ignore
    CacheConfig = None  # type: ignore
    CacheKey = None  # type: ignore

# Import LLM service base
try:
    from .llm_service_base import (
        LLMServiceBase,
        LLMServiceError,
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMConnectionError,
        LLMResponseError,
    )
except ModuleNotFoundError:
    LLMServiceBase = None  # type: ignore
    LLMServiceError = RuntimeError  # type: ignore
    LLMAuthenticationError = RuntimeError  # type: ignore
    LLMRateLimitError = RuntimeError  # type: ignore
    LLMConnectionError = RuntimeError  # type: ignore
    LLMResponseError = RuntimeError  # type: ignore

# Import DeepSeek service
try:
    from .deepseek_service import (
        DeepSeekService,
        DeepSeekError,
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        APIResponseError,
    )
except ModuleNotFoundError:
    DeepSeekService = None  # type: ignore
    DeepSeekError = RuntimeError  # type: ignore
    AuthenticationError = RuntimeError  # type: ignore
    RateLimitError = RuntimeError  # type: ignore
    APIConnectionError = RuntimeError  # type: ignore
    APIResponseError = RuntimeError  # type: ignore

# Import Local model service
try:
    from .local_model_service import (
        LocalModelService,
        LocalModelConfig,
        LocalModelError,
        ModelNotFoundError,
        ModelDownloadError,
        ModelLoadError,
    )
except ModuleNotFoundError:
    LocalModelService = None  # type: ignore
    LocalModelConfig = None  # type: ignore
    LocalModelError = RuntimeError  # type: ignore
    ModelNotFoundError = RuntimeError  # type: ignore
    ModelDownloadError = RuntimeError  # type: ignore
    ModelLoadError = RuntimeError  # type: ignore

# Import Fallback model service
try:
    from .fallback_model_service import (
        FallbackModelService,
        FallbackMode,
    )
except ModuleNotFoundError:
    FallbackModelService = None  # type: ignore
    FallbackMode = None  # type: ignore

# Import Summarizer service
try:
    from .summarizer_service import (
        SummarizerService,
        SummarizerConfig,
        SummarizerResult,
        SummarizationStatus,
        GenerationMetrics,
    )
except ModuleNotFoundError:
    SummarizerService = None  # type: ignore
    SummarizerConfig = None  # type: ignore 
    SummarizerResult = None  # type: ignore
    SummarizationStatus = None  # type: ignore
    GenerationMetrics = None  # type: ignore

# Import new services
from .video_downloader import VideoDownloader
from .caption_fallback import (
    FallbackStrategy, WhisperFallbackStrategy, 
    ExternalWhisperFallbackStrategy, FallbackChain
)
from .subtitle_converter import SubtitleConverter
from .youtube_utils import YouTubeValidator, VideoMetadata, MetadataExtractor
from .transcript_segmenter import (
    TranscriptSegmenter, Segment, SegmentManager, 
    TokenizerInterface, SimpleTokenizer
)
from .prompt_templates import (
    PromptAssembler, SectionTemplate, 
    MEDIUM_TEMPLATES, TONE_SPECIFIC_GUIDANCE
)
from .article_structure_generator import (
    ArticleStructureGenerator, ArticleFormatConfig
)
from .token_usage_tracker import (
    TokenUsageTracker, TokenUsageStats, TokenOptimizer,
    UsagePeriod, UsageRecord, TokenBudgetExceededError
)

__all__ = [
    "YtDlpWrapper",
    "YtDlpError",
    "Caption",
    "CaptionLine",
    "CaptionMetadata",
    "CaptionError",
    "ParserFactory",
    "ParserError",
    "SrtParser",
    "VttParser",
    "CaptionService",
    "CaptionCache",
    "CacheConfig",
    "CacheKey",
    # LLM Service Base
    "LLMServiceBase",
    "LLMServiceError",
    "LLMAuthenticationError",
    "LLMRateLimitError", 
    "LLMConnectionError",
    "LLMResponseError",
    # DeepSeek
    "DeepSeekService",
    "DeepSeekError",
    "AuthenticationError",
    "RateLimitError",
    "APIConnectionError",
    "APIResponseError",
    # Local Model Service
    "LocalModelService",
    "LocalModelConfig",
    "LocalModelError",
    "ModelNotFoundError",
    "ModelDownloadError",
    "ModelLoadError",
    # Fallback Model Service
    "FallbackModelService",
    "FallbackMode",
    # Summarizer
    "SummarizerService",
    "SummarizerConfig",
    "SummarizerResult",
    "SummarizationStatus",
    "GenerationMetrics",
    # New services
    "VideoDownloader",
    "FallbackStrategy",
    "WhisperFallbackStrategy",
    "ExternalWhisperFallbackStrategy",
    "FallbackChain",
    "SubtitleConverter",
    "YouTubeValidator",
    "VideoMetadata",
    "MetadataExtractor",
    "TranscriptSegmenter",
    "Segment",
    "SegmentManager",
    "TokenizerInterface",
    "SimpleTokenizer",
    "PromptAssembler",
    "SectionTemplate",
    "MEDIUM_TEMPLATES",
    "TONE_SPECIFIC_GUIDANCE",
    "ArticleStructureGenerator",
    "ArticleFormatConfig",
    # Token usage tracker
    "TokenUsageTracker",
    "TokenUsageStats",
    "TokenOptimizer",
    "UsagePeriod",
    "UsageRecord",
    "TokenBudgetExceededError"
]

try:
    __version__ = metadata.version("yt-dlp")
except metadata.PackageNotFoundError:  # type: ignore[attr-defined]
    __version__ = "not-installed" 