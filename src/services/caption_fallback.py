"""Fallback strategies for caption extraction.

This module implements Task 3.6 (Develop fallback options for missing captions) by providing:

* `FallbackStrategy` - Interface for caption fallback strategies
* `WhisperFallbackStrategy` - A fallback strategy using Whisper for speech-to-text
* `FallbackChain` - A chain of fallback strategies to try in sequence

These fallback strategies are used when primary caption retrieval methods fail.
"""

import os
import logging
import tempfile
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from .caption_model import Caption, CaptionMetadata, CaptionLine, CaptionError
from .yt_dlp_wrapper import YtDlpWrapper

class FallbackStrategy(ABC):
    """Interface for caption fallback strategies.
    
    A fallback strategy is used when primary caption retrieval methods fail.
    Each strategy should implement the `try_get_caption` method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the fallback strategy."""
        pass
    
    @abstractmethod
    def try_get_caption(
        self, 
        url: str, 
        language: str, 
        **kwargs
    ) -> Optional[Caption]:
        """Try to get captions using a fallback method.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str
            Language code (e.g., 'en', 'fr')
        **kwargs : Any
            Additional parameters specific to the fallback strategy
            
        Returns
        -------
        Optional[Caption]
            Caption object if fallback was successful, None otherwise
        """
        pass
    
    @property
    def priority(self) -> int:
        """Get the priority of the fallback strategy.
        
        Higher values indicate higher priority.
        Default is 0.
        
        Returns
        -------
        int
            Priority value
        """
        return 0


class WhisperFallbackStrategy(FallbackStrategy):
    """A fallback strategy using Whisper for speech-to-text.
    
    This strategy extracts audio from the video and uses Whisper to 
    generate captions when normal caption extraction fails.
    """
    
    def __init__(
        self, 
        yt_dlp_wrapper: YtDlpWrapper, 
        whisper_model: str = "small", 
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the Whisper fallback strategy.
        
        Parameters
        ----------
        yt_dlp_wrapper : YtDlpWrapper
            Instance of YtDlpWrapper for downloading audio
        whisper_model : str, default "small"
            Whisper model size: 'tiny', 'base', 'small', 'medium', or 'large'
        logger : Optional[logging.Logger], default None
            Logger for recording issues
        """
        self.yt_dlp = yt_dlp_wrapper
        self.whisper_model = whisper_model
        self.logger = logger or logging.getLogger(__name__)
    
    @property
    def name(self) -> str:
        """Get the name of the fallback strategy."""
        return f"whisper-{self.whisper_model}"
    
    @property
    def priority(self) -> int:
        """Get the priority of the fallback strategy."""
        # Higher priority than default (0)
        return 10
    
    def try_get_caption(
        self, 
        url: str, 
        language: str, 
        **kwargs
    ) -> Optional[Caption]:
        """Try to get captions using Whisper speech-to-text.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str
            Language code (e.g., 'en', 'fr')
        **kwargs : Any
            Additional parameters, including:
            - video_id: Optional[str] - Extracted video ID
            - whisper_kwargs: Optional[Dict[str, Any]] - Additional Whisper parameters
            
        Returns
        -------
        Optional[Caption]
            Caption object if fallback was successful, None otherwise
        """
        video_id = kwargs.get("video_id")
        whisper_kwargs = kwargs.get("whisper_kwargs", {})
        
        try:
            self.logger.info(f"Trying Whisper fallback for video {url}")
            
            # Create temporary directory for audio file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Step 1: Download audio
                audio_file = self._download_audio(url, temp_path)
                if not audio_file or not os.path.exists(audio_file):
                    self.logger.warning(f"Failed to download audio for {url}")
                    return None
                
                # Step 2: Process with Whisper
                result = self._run_whisper(
                    audio_file, 
                    language=language, 
                    **whisper_kwargs
                )
                
                if not result:
                    self.logger.warning(f"Whisper processing failed for {url}")
                    return None
                
                # Step 3: Create Caption object
                return self._create_caption_from_result(
                    result, 
                    url, 
                    language, 
                    video_id
                )
                
        except Exception as e:
            self.logger.error(f"Whisper fallback failed: {e}")
            return None
    
    def _download_audio(self, url: str, output_dir: Path) -> Optional[str]:
        """Download audio from the YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        output_dir : Path
            Directory to save the audio file
            
        Returns
        -------
        Optional[str]
            Path to the downloaded audio file, or None if download failed
        """
        try:
            # Use yt-dlp to download audio only
            output_template = str(output_dir / "%(id)s.%(ext)s")
            
            result = self.yt_dlp.download_audio(
                url=url,
                output_template=output_template,
                audio_format="mp3",
                audio_quality="192k"
            )
            
            if not result or not result.get("filepath"):
                return None
                
            return result["filepath"]
            
        except Exception as e:
            self.logger.error(f"Error downloading audio: {e}")
            return None
    
    def _run_whisper(
        self, 
        audio_file: str, 
        language: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Run Whisper on the audio file.
        
        Parameters
        ----------
        audio_file : str
            Path to the audio file
        language : str
            Language code (e.g., 'en', 'fr')
        **kwargs : Any
            Additional Whisper parameters
            
        Returns
        -------
        Optional[Dict[str, Any]]
            Whisper result dictionary, or None if processing failed
        """
        try:
            # Check if whisper is installed
            try:
                import whisper
            except ImportError:
                self.logger.error(
                    "Whisper not installed. Install with 'pip install -U openai-whisper'"
                )
                return None
            
            # Load model
            model = whisper.load_model(self.whisper_model)
            
            # Convert language code to Whisper format if needed
            whisper_language = language
            if len(language) > 2:
                # Use first two characters for whisper
                whisper_language = language[:2]
            
            # Transcribe audio
            # Default to language detection unless language is specified
            transcribe_kwargs = {
                "verbose": False,
            }
            
            if whisper_language:
                transcribe_kwargs["language"] = whisper_language
                
            # Add any additional kwargs
            transcribe_kwargs.update(kwargs)
            
            # Run transcription
            result = model.transcribe(audio_file, **transcribe_kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error running Whisper: {e}")
            return None
    
    def _create_caption_from_result(
        self, 
        result: Dict[str, Any], 
        url: str, 
        language: str,
        video_id: Optional[str] = None
    ) -> Caption:
        """Create a Caption object from Whisper result.
        
        Parameters
        ----------
        result : Dict[str, Any]
            Whisper result dictionary
        url : str
            YouTube video URL
        language : str
            Language code
        video_id : Optional[str], default None
            YouTube video ID, if available
            
        Returns
        -------
        Caption
            Caption object with metadata and lines
        """
        # Create metadata
        metadata = CaptionMetadata(
            video_id=video_id or "unknown",
            language_code=language,
            language_name=result.get("language", "Unknown"),
            is_auto_generated=True,
            format="whisper",
            source_url=url,
            caption_type="auto_generated",
            has_speaker_identification=False,
            provider="whisper",
            is_default=False,
            quality_score=result.get("confidence", 0.0)
        )
        
        # Create caption
        caption = Caption(metadata=metadata)
        
        # Add lines from segments
        for i, segment in enumerate(result.get("segments", [])):
            caption.lines.append(
                CaptionLine(
                    index=i,
                    start_time=segment.get("start", 0.0),
                    end_time=segment.get("end", 0.0),
                    text=segment.get("text", "").strip()
                )
            )
        
        return caption


class ExternalWhisperFallbackStrategy(FallbackStrategy):
    """Fallback strategy using external Whisper CLI.
    
    This strategy uses the whisper CLI tool instead of importing the whisper library,
    which is useful when running in environments where the library can't be installed.
    """
    
    def __init__(
        self, 
        yt_dlp_wrapper: YtDlpWrapper, 
        whisper_cmd: str = "whisper", 
        whisper_model: str = "small", 
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the external Whisper fallback strategy.
        
        Parameters
        ----------
        yt_dlp_wrapper : YtDlpWrapper
            Instance of YtDlpWrapper for downloading audio
        whisper_cmd : str, default "whisper"
            Command to run Whisper
        whisper_model : str, default "small"
            Whisper model size: 'tiny', 'base', 'small', 'medium', or 'large'
        logger : Optional[logging.Logger], default None
            Logger for recording issues
        """
        self.yt_dlp = yt_dlp_wrapper
        self.whisper_cmd = whisper_cmd
        self.whisper_model = whisper_model
        self.logger = logger or logging.getLogger(__name__)
    
    @property
    def name(self) -> str:
        """Get the name of the fallback strategy."""
        return f"external-whisper-{self.whisper_model}"
    
    @property
    def priority(self) -> int:
        """Get the priority of the fallback strategy."""
        # Slightly lower priority than direct Whisper integration
        return 5
    
    def try_get_caption(
        self, 
        url: str, 
        language: str, 
        **kwargs
    ) -> Optional[Caption]:
        """Try to get captions using external Whisper CLI.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str
            Language code (e.g., 'en', 'fr')
        **kwargs : Any
            Additional parameters
            
        Returns
        -------
        Optional[Caption]
            Caption object if fallback was successful, None otherwise
        """
        video_id = kwargs.get("video_id")
        
        try:
            self.logger.info(f"Trying external Whisper fallback for video {url}")
            
            # Create temporary directory for audio and output files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Step 1: Download audio
                audio_file = self._download_audio(url, temp_path)
                if not audio_file or not os.path.exists(audio_file):
                    self.logger.warning(f"Failed to download audio for {url}")
                    return None
                
                # Step 2: Process with Whisper CLI
                srt_file = self._run_whisper_cli(audio_file, language)
                if not srt_file or not os.path.exists(srt_file):
                    self.logger.warning(f"Whisper CLI processing failed for {url}")
                    return None
                
                # Step 3: Read SRT file
                with open(srt_file, "r", encoding="utf-8") as f:
                    srt_content = f.read()
                
                # Step 4: Create Caption object from SRT content
                from .subtitle_parser import ParserFactory
                
                metadata = CaptionMetadata(
                    video_id=video_id or "unknown",
                    language_code=language,
                    language_name="Unknown",
                    is_auto_generated=True,
                    format="srt",
                    source_url=url,
                    caption_type="auto_generated",
                    has_speaker_identification=False,
                    provider="whisper-cli",
                    is_default=False
                )
                
                return ParserFactory.parse_subtitle(
                    content=srt_content,
                    metadata=metadata,
                    format_name="srt"
                )
                
        except Exception as e:
            self.logger.error(f"External Whisper fallback failed: {e}")
            return None
    
    def _download_audio(self, url: str, output_dir: Path) -> Optional[str]:
        """Download audio from the YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        output_dir : Path
            Directory to save the audio file
            
        Returns
        -------
        Optional[str]
            Path to the downloaded audio file, or None if download failed
        """
        try:
            # Use yt-dlp to download audio only
            output_template = str(output_dir / "%(id)s.%(ext)s")
            
            result = self.yt_dlp.download_audio(
                url=url,
                output_template=output_template,
                audio_format="mp3",
                audio_quality="192k"
            )
            
            if not result or not result.get("filepath"):
                return None
                
            return result["filepath"]
            
        except Exception as e:
            self.logger.error(f"Error downloading audio: {e}")
            return None
    
    def _run_whisper_cli(self, audio_file: str, language: str) -> Optional[str]:
        """Run Whisper CLI on the audio file.
        
        Parameters
        ----------
        audio_file : str
            Path to the audio file
        language : str
            Language code (e.g., 'en', 'fr')
            
        Returns
        -------
        Optional[str]
            Path to the SRT file, or None if processing failed
        """
        try:
            # Convert language code to Whisper format if needed
            whisper_language = language
            if len(language) > 2:
                # Use first two characters for whisper
                whisper_language = language[:2]
            
            # Get the audio file without extension
            audio_file_base = os.path.splitext(audio_file)[0]
            
            # SRT file will be created as {audio_file_base}.srt
            srt_file = f"{audio_file_base}.srt"
            
            # Build command
            cmd = [
                self.whisper_cmd,
                audio_file,
                "--model", self.whisper_model,
                "--output-format", "srt"
            ]
            
            # Add language if specified
            if whisper_language:
                cmd.extend(["--language", whisper_language])
            
            # Run command
            self.logger.info(f"Running Whisper command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Whisper CLI failed: {stderr}")
                return None
            
            # Check if the SRT file was created
            if not os.path.exists(srt_file):
                self.logger.error(f"Whisper CLI did not create SRT file: {srt_file}")
                return None
                
            return srt_file
            
        except Exception as e:
            self.logger.error(f"Error running Whisper CLI: {e}")
            return None


class FallbackChain:
    """A chain of fallback strategies to try in sequence.
    
    This class maintains a prioritized list of fallback strategies
    and tries them in order until one succeeds.
    """
    
    def __init__(
        self, 
        strategies: Optional[List[FallbackStrategy]] = None, 
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the fallback chain.
        
        Parameters
        ----------
        strategies : Optional[List[FallbackStrategy]], default None
            List of fallback strategies to use
        logger : Optional[logging.Logger], default None
            Logger for recording issues
        """
        self.strategies = strategies or []
        self.logger = logger or logging.getLogger(__name__)
    
    def add_strategy(self, strategy: FallbackStrategy) -> None:
        """Add a fallback strategy to the chain.
        
        Parameters
        ----------
        strategy : FallbackStrategy
            Fallback strategy to add
        """
        self.strategies.append(strategy)
        # Sort strategies by priority (higher first)
        self.strategies.sort(key=lambda s: s.priority, reverse=True)
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a fallback strategy from the chain.
        
        Parameters
        ----------
        strategy_name : str
            Name of the strategy to remove
            
        Returns
        -------
        bool
            True if the strategy was removed, False if not found
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.name == strategy_name:
                del self.strategies[i]
                return True
        return False
    
    def get_strategies(self) -> List[str]:
        """Get the names of all strategies in the chain.
        
        Returns
        -------
        List[str]
            List of strategy names
        """
        return [strategy.name for strategy in self.strategies]
    
    def try_all(
        self, 
        url: str, 
        language: str, 
        **kwargs
    ) -> Optional[Caption]:
        """Try all fallback strategies in order.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str
            Language code (e.g., 'en', 'fr')
        **kwargs : Any
            Additional parameters passed to each strategy
            
        Returns
        -------
        Optional[Caption]
            Caption object from the first successful strategy, or None if all fail
        """
        if not self.strategies:
            self.logger.warning("No fallback strategies available")
            return None
        
        for strategy in self.strategies:
            self.logger.info(f"Trying fallback strategy: {strategy.name}")
            caption = strategy.try_get_caption(url, language, **kwargs)
            if caption:
                self.logger.info(f"Fallback strategy '{strategy.name}' succeeded")
                return caption
                
        self.logger.warning("All fallback strategies failed")
        return None 