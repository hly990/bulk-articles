from __future__ import annotations

"""Lightweight wrapper around the ``yt_dlp`` Python API / CLI.

This helper fulfils *task 2.1 (Set up **yt‑dlp** library integration)*:

1. Checks that the library is importable at runtime.
2. Provides convenience methods to:
   • validate installation
   • fetch basic video metadata (without download)
   • execute arbitrary yt‑dlp CLI commands (fallback / advanced)
3. Surfaces clear, typed exceptions for UI‑layer handling.
"""

from pathlib import Path
import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Union
import io
import contextlib

try:
    import yt_dlp
    from yt_dlp.utils import DownloadError
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

__all__ = [
    "YtDlpError",
    "YtDlpWrapper",
]


class YtDlpError(RuntimeError):
    """Common base error for all wrapper‑raised issues."""


class YtDlpWrapper:
    """Simple façade over *yt‑dlp* for unified error handling.

    Parameters
    ----------
    ydl_opts : dict | None
        Extra options forwarded to :class:`yt_dlp.YoutubeDL`.  The wrapper adds
        a few sensible defaults (quiet extraction, no download) which can be
        overridden here.
    logger : logging.Logger | None
        Logger to use.  If *None*, the module‑level logger is employed.
    """

    # Minimal default YDL options – callers may override as needed
    _BASE_OPTS: Dict[str, Any] = {
        "no_warnings": True,          # No warnings about unimportant issues
        "ignoreerrors": True,         # Skip unavailable videos in a playlist
        "no_color": True,             # Terminal colors DNE in subprocess outputs
        "noprogress": True,           # Don't stall while loading
        "quiet": True,                # Don't print output (when used with CLI)
        "extract_flat": True,         # No info extraction from playlists
        "skip_download": True,        # Skip actual video download when just getting info
        # Subtitle related options
        "writesubtitles": False,      # Download subs alongside video by default
        "writeautomaticsub": False,   # Download auto-generated subs
        "subtitleslangs": ["en"],     # Default to English subs
        "subtitlesformat": "srt",     # Default subtitle format
    }

    def __init__(
        self,
        ydl_opts: Optional[Dict[str, Any]] = None,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.ydl_opts: Dict[str, Any] = {**self._BASE_OPTS, **(ydl_opts or {})}
        self.logger.debug("YtDlpWrapper initialised with opts: %s", self.ydl_opts)

        # Validate environment early so UI 能够在启动阶段给出提示
        self._ensure_library_available()

    # ---------------------------------------------------------------------
    # Installation helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _ensure_library_available() -> None:
        """Raise :class:`YtDlpError` if *yt‑dlp* is not importable."""

        if not HAS_YT_DLP:
            raise YtDlpError(
                "yt-dlp library is not installed. Run 'pip install yt-dlp' or add it to requirements.txt"  # noqa: E501
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def is_installed(cls) -> bool:
        """Return **True** when *yt‑dlp* is importable (Python package level)."""
        return HAS_YT_DLP

    @staticmethod
    def executable_exists() -> bool:
        """Check if the *yt-dlp* CLI executable is in *PATH*."""
        return shutil.which("yt-dlp") is not None

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Fetches video metadata without downloading the actual video.

        Parameters
        ----------
        url : str
            URL of the video to get info for

        Returns
        -------
        Dict[str, Any]
            Dictionary of video metadata

        Raises
        ------
        YtDlpError
            If there's an error fetching the video info
        """
        options = {
            **self._BASE_OPTS,
            'skip_download': True,
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except (yt_dlp.DownloadError, yt_dlp.ExtractorError) as exc:
            error_msg = str(exc)
            if '404' in error_msg:
                raise YtDlpError(f"Video does not exist: {error_msg}")
            elif 'Private video' in error_msg:
                raise YtDlpError(f"Cannot access private video: {error_msg}")
            elif 'sign in' in error_msg.lower():
                raise YtDlpError(f"Video requires login: {error_msg}")
            else:
                raise YtDlpError(f"Error fetching video info: {error_msg}")

    # ------------------------------------------------------------------
    # CLI fallback – occasionally needed for features not exposed in API
    # ------------------------------------------------------------------
    def run_cli(self, args: List[str]) -> str:
        """Execute *yt-dlp* via subprocess and return *stdout* text.

        Parameters
        ----------
        args
            List of arguments *excluding* the program name, e.g. ``["--version"]``.
        """
        if not self.executable_exists():
            raise YtDlpError("yt-dlp executable not found in PATH; cannot run CLI command.")

        cmd = ["yt-dlp", *args]
        self.logger.debug("Running yt-dlp CLI: %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error("yt-dlp CLI failed: %s", exc.stdout)
            raise YtDlpError(exc.stdout) from exc

        self.logger.debug("yt-dlp CLI output: %s", proc.stdout[:4000])
        return proc.stdout

    # ------------------------------------------------------------------
    # Subtitle extraction
    # ------------------------------------------------------------------
    def list_available_subtitles(self, url: str) -> Dict[str, Dict[str, Any]]:
        """Get a list of available subtitle tracks for a video.
        
        Parameters
        ----------
        url : str
            URL of the video to get subtitles for
            
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping language codes to subtitle information
            
        Raises
        ------
        YtDlpError
            If there's an error fetching the subtitle info
        """
        try:
            # First try to get from video info which is more reliable
            info = self.get_video_info(url)
            if info and 'subtitles' in info:
                return self._extract_subtitles_from_info(info)
                
            # Fallback to CLI command
            output = self.run_cli(
                url=url,
                extra_args=['--list-subs'],
                capture_stdout=True
            )
            
            return self._parse_subtitle_list_output(output)
        except Exception as exc:
            raise YtDlpError(f"Error listing available subtitles: {exc}")

    def download_subtitle(
        self, 
        url: str, 
        lang_code: str, 
        output_path: Union[str, Path],
        auto_generated: bool = False,
        format: str = 'srt'
    ) -> Path:
        """Download subtitle for a specific language.
        
        Parameters
        ----------
        url : str
            URL of the video to download subtitles for
        lang_code : str
            Language code of the subtitle to download (e.g., 'en', 'es', 'fr')
        output_path : Union[str, Path]
            Path to save the subtitle file
        auto_generated : bool, default False
            Whether to download auto-generated subtitles
        format : str, default 'srt'
            Format of the subtitle file ('srt', 'vtt', 'json', etc.)
            
        Returns
        -------
        Path
            Path to the downloaded subtitle file
            
        Raises
        ------
        YtDlpError
            If there's an error downloading the subtitle
        """
        output_path = Path(output_path)
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        extra_args = []
        
        # Add format option
        extra_args.extend(['--sub-format', format])
        
        # Add language option
        extra_args.extend(['--sub-langs', lang_code])
        
        # Add auto-generated option if specified
        if auto_generated:
            extra_args.append('--write-auto-sub')
        else:
            extra_args.append('--write-sub')
        
        # Add output template
        output_template = str(output_path)
        extra_args.extend(['--output', output_template])
        
        try:
            self.run_cli(
                url=url,
                extra_args=extra_args,
                capture_stdout=True
            )
            
            # Check if file exists
            if not output_path.exists():
                raise YtDlpError(f"Subtitle file not generated at {output_path}")
            
            return output_path
        except Exception as exc:
            raise YtDlpError(f"Error downloading subtitle: {exc}")

    # ------------------------------------------------------------------
    # Internal subtitle parsing helpers 
    # ------------------------------------------------------------------
    def _parse_subtitle_list_output(self, output: str) -> Dict[str, Dict[str, Any]]:
        """Parse the output of the --list-subs command.
        
        Parameters
        ----------
        output : str
            Output of the yt-dlp --list-subs command
            
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping language codes to subtitle information
        """
        result = {}
        
        # Find the section for available subtitles
        lines = output.split('\n')
        
        in_subtitles_section = False
        in_auto_subtitles_section = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check for section headers
            if 'Available subtitles' in line:
                in_subtitles_section = True
                in_auto_subtitles_section = False
                continue
            elif 'Available automatic captions' in line:
                in_subtitles_section = False
                in_auto_subtitles_section = True
                continue
            elif line.startswith('------'):
                # Skip separator lines
                continue
            
            # Process subtitle lines when in a subtitle section
            if in_subtitles_section or in_auto_subtitles_section:
                # Format is typically: "en English"
                parts = line.split(' ', 1)
                if len(parts) < 2:
                    continue
                    
                lang_code = parts[0]
                lang_name = parts[1] if len(parts) > 1 else lang_code
                
                result[lang_code] = {
                    "name": lang_name,
                    "is_auto": in_auto_subtitles_section,
                    "formats": ['vtt', 'srt', 'json'],  # Supported formats
                }
        
        return result

    def _extract_subtitles_from_info(self, info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract subtitle information from the video info dictionary.
        
        Parameters
        ----------
        info : Dict[str, Any]
            Video info dictionary from yt-dlp
            
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping language codes to subtitle information
        """
        result = {}
        
        # Process regular subtitles
        if 'subtitles' in info and info['subtitles']:
            for lang_code, formats in info['subtitles'].items():
                # Some languages might have multiple format options
                result[lang_code] = {
                    "name": self._get_language_name(lang_code),
                    "is_auto": False,
                    "formats": [fmt.get('ext', 'unknown') for fmt in formats] if isinstance(formats, list) else ['vtt', 'srt']
                }
        
        # Process auto-generated subtitles
        if 'automatic_captions' in info and info['automatic_captions']:
            for lang_code, formats in info['automatic_captions'].items():
                # Skip langs that we already have manual captions for
                if lang_code in result:
                    continue
                    
                result[lang_code] = {
                    "name": self._get_language_name(lang_code),
                    "is_auto": True,
                    "formats": [fmt.get('ext', 'unknown') for fmt in formats] if isinstance(formats, list) else ['vtt', 'srt']
                }
        
        return result

    @staticmethod
    def _get_language_name(lang_code: str) -> str:
        """Convert language code to human-readable name.
        
        Parameters
        ----------
        lang_code : str
            ISO language code (e.g., 'en', 'es', 'fr')
            
        Returns
        -------
        str
            Human-readable language name
        """
        language_map = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            # Add more languages as needed
        }
        
        return language_map.get(lang_code, f'Unknown ({lang_code})')

    # ------------------------------------------------------------------
    # Video download methods
    # ------------------------------------------------------------------
    def download_video(
        self, 
        url: str, 
        output_path: Union[str, Path],
        format: str = "best",
        extra_options: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Download a video from the given URL.
        
        Parameters
        ----------
        url : str
            YouTube video URL
        output_path : str | Path
            Path to save the video file
        format : str
            Format code for the video. Default is "best" for best quality.
            Common options: "best", "bestvideo+bestaudio", "worst"
        extra_options : Dict[str, Any] | None
            Additional yt-dlp options
            
        Returns
        -------
        Path
            Path to the downloaded video file
            
        Raises
        ------
        YtDlpError
            If there's an error downloading the video
        """
        output_path = Path(output_path)
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        extra_args = []
        
        # Add format option
        extra_args.extend(['-f', format])
        
        # Add output template
        output_template = str(output_path)
        extra_args.extend(['--output', output_template])
        
        # Merge any extra options into our YDL options
        ydl_opts = self._BASE_OPTS.copy()
        if extra_options:
            ydl_opts.update(extra_options)
        
        # Override quiet setting as we want to download
        ydl_opts['quiet'] = False
        ydl_opts['no_warnings'] = False
        ydl_opts['noprogress'] = False
        
        # We actually want to download the file
        if 'extract_flat' in ydl_opts:
            del ydl_opts['extract_flat']
        if 'skip_download' in ydl_opts:
            del ydl_opts['skip_download']
        
        try:
            self._ensure_library_available()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
            # Try to find the downloaded file if not already at expected location
            if not output_path.exists():
                # If output template has wildcards, we need to check what file was created
                if "*" in str(output_path) or "%" in str(output_path):
                    # Get the directory of the output template
                    output_dir = output_path.parent
                    
                    # Get the most recently modified file in that directory
                    files = list(output_dir.glob("*"))
                    if files:
                        latest_file = max(files, key=lambda p: p.stat().st_mtime)
                        return latest_file
                
                raise YtDlpError(f"Video file not generated at {output_path}")
            
            return output_path
        except Exception as exc:
            raise YtDlpError(f"Error downloading video: {exc}")

    # ------------------------------------------------------------------
    # Video processing methods
    # ------------------------------------------------------------------
    def extract_keyframes(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path],
        interval: int = 300,  # Default: extract every 5 minutes
        max_frames: Optional[int] = 20,
        min_scene_change: float = 0.3
    ) -> List[Path]:
        """Extract keyframes from a downloaded video.
        
        Parameters
        ----------
        video_path : str | Path
            Path to the video file
        output_dir : str | Path
            Directory to save extracted keyframes
        interval : int
            Time interval in seconds between frames (default: 300 seconds/5 minutes)
        max_frames : int | None
            Maximum number of frames to extract (default: 20)
            Set to None for no limit
        min_scene_change : float
            Minimum scene change detection threshold (0.0-1.0)
            Higher values detect only significant scene changes
            
        Returns
        -------
        List[Path]
            List of paths to the extracted keyframe image files
            
        Raises
        ------
        YtDlpError
            If there's an error extracting keyframes
        """
        try:
            # Ensure input file exists
            video_path = Path(video_path)
            if not video_path.exists():
                raise YtDlpError(f"Video file not found: {video_path}")
            
            # Create output directory if it doesn't exist
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for ffmpeg
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                raise YtDlpError("ffmpeg is required but not found on the system path")
            
            # Option 1: Extract frames at regular intervals
            if interval > 0:
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-vf", f"select='isnan(prev_selected_t) or gte(t-prev_selected_t,{interval})'",
                    "-vsync", "0", "-frame_pts", "1", "-q:v", "2",
                    f"{output_dir}/frame_%04d.jpg"
                ]
                
                if max_frames:
                    cmd[4] = f"select='isnan(prev_selected_t) or gte(t-prev_selected_t,{interval})':gte(n\\,0):lte(n\\,{max_frames-1})'"
            
            # Option 2: Extract based on scene changes
            else:
                cmd = [
                    "ffmpeg", "-i", str(video_path),
                    "-vf", f"select='gt(scene,{min_scene_change})',metadata=print:file={output_dir}/scenes.txt",
                    "-vsync", "0", "-frame_pts", "1", "-q:v", "2",
                    f"{output_dir}/frame_%04d.jpg"
                ]
                
                if max_frames:
                    cmd[4] = f"select='gt(scene,{min_scene_change})':gte(n\\,0):lte(n\\,{max_frames-1})'"
            
            # Run ffmpeg command
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Get list of extracted frames
            frames = sorted(list(output_dir.glob("frame_*.jpg")))
            
            # If no frames were extracted, raise an error
            if not frames:
                raise YtDlpError("No keyframes were extracted from the video")
                
            return frames
            
        except subprocess.SubprocessError as exc:
            raise YtDlpError(f"Error running ffmpeg to extract keyframes: {exc}")
        except Exception as exc:
            raise YtDlpError(f"Error extracting keyframes: {exc}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def save_json(data: Dict[str, Any], output_path: str | Path) -> None:
        """Utility helper: dump *data* to *output_path* in UTF‑8 JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf‑8")

    # ------------------------------------------------------------------
    # Subtitle processing methods
    # ------------------------------------------------------------------
    def list_subtitles(self, url: str) -> Dict[str, List[Dict[str, str]]]:
        """List all available subtitles for a YouTube video.
        
        Parameters
        ----------
        url : str
            URL of the YouTube video
            
        Returns
        -------
        Dict[str, List[Dict[str, str]]]
            Dictionary with subtitle information:
            {
                'automatic': [
                    {'language': 'en', 'format': 'vtt', 'ext': 'vtt', 'name': 'English'},
                    ...
                ],
                'manual': [
                    {'language': 'fr', 'format': 'vtt', 'ext': 'vtt', 'name': 'French'},
                    ...
                ]
            }
            
        Raises
        ------
        YtDlpError
            If there's an error fetching subtitle information
        """
        try:
            # Create options with list-subs but without downloading
            ydl_opts = {
                'skip_download': True,
                'listsubtitles': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            # Create a yt-dlp instance with memory output
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    # Trigger subtitle listing
                    ydl.list_subtitles(info)
            
            subtitle_output = output_buffer.getvalue()
            
            # Parse the output to get subtitle information
            result = {
                'automatic': [],
                'manual': []
            }
            
            current_section = None
            # If no subtitles found
            if "There are no subtitles for this video" in subtitle_output:
                return result
                
            # Parse the output
            for line in subtitle_output.split('\n'):
                line = line.strip()
                
                if 'Available automatic captions' in line:
                    current_section = 'automatic'
                elif 'Available subtitles' in line:
                    current_section = 'manual'
                elif current_section and line and line[0].isalpha():
                    # Each line format is typically: "en:English [default]"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        language_code = parts[0].strip()
                        language_name = parts[1].strip()
                        
                        # Remove any [default] or other annotations
                        if '[' in language_name:
                            language_name = language_name.split('[')[0].strip()
                            
                        subtitle_info = {
                            'language': language_code,
                            'name': language_name,
                            'format': 'vtt',
                            'ext': 'vtt'
                        }
                        
                        result[current_section].append(subtitle_info)
            
            return result
            
        except Exception as exc:
            raise YtDlpError(f"Error listing subtitles: {exc}")
    
    def download_subtitle(
        self, 
        url: str, 
        output_path: Union[str, Path], 
        language: str = 'en',
        formats: List[str] = ['vtt', 'srt'],
        source: str = 'any'  # 'manual', 'automatic', or 'any'
    ) -> Path:
        """Download subtitles for a YouTube video.
        
        Parameters
        ----------
        url : str
            URL of the YouTube video
        output_path : str | Path
            Path to save the subtitle file
        language : str
            Language code for the subtitle (default: 'en')
        formats : List[str]
            Preferred subtitle formats in order of preference (default: ['vtt', 'srt'])
        source : str
            Source of subtitles: 'manual', 'automatic', or 'any' (default: 'any')
            
        Returns
        -------
        Path
            Path to the downloaded subtitle file
            
        Raises
        ------
        YtDlpError
            If there's an error downloading subtitles or if the requested language is not available
        """
        try:
            output_path = Path(output_path)
            
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # First check if the requested language is available
            available_subtitles = self.list_subtitles(url)
            
            # Determine available subtitle sources based on the 'source' parameter
            sources_to_check = []
            if source == 'any':
                sources_to_check = ['manual', 'automatic']
            else:
                sources_to_check = [source]
            
            # Check if requested language is available in specified sources
            language_available = False
            selected_source = None
            
            for src in sources_to_check:
                for sub in available_subtitles.get(src, []):
                    if sub['language'] == language:
                        language_available = True
                        selected_source = src
                        break
                if language_available:
                    break
            
            if not language_available:
                raise YtDlpError(f"Subtitles in language '{language}' are not available")
            
            # Create yt-dlp options for subtitle download
            ydl_opts = {
                'skip_download': True,
                'subtitleslangs': [language],
                'writesubtitles': True,
                'outtmpl': str(output_path.with_suffix('')),
                'quiet': True,
                'no_warnings': True,
            }
            
            # Select source type (auto or regular)
            if selected_source == 'automatic':
                ydl_opts['writeautomaticsub'] = True
            else:
                ydl_opts['writesubtitles'] = True
            
            # Format preference
            for fmt in formats:
                ydl_opts[f'subtitlesformat'] = fmt
                
                # Try to download with current format
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Check if file was created with current format
                expected_file = output_path.with_suffix(f'.{language}.{fmt}')
                if expected_file.exists():
                    # Rename file to the requested output path if needed
                    if expected_file != output_path:
                        shutil.move(expected_file, output_path)
                    return output_path
            
            # If we reach this point, none of the formats were downloaded successfully
            raise YtDlpError(f"Failed to download subtitles in any of the requested formats: {formats}")
            
        except Exception as exc:
            raise YtDlpError(f"Error downloading subtitles: {exc}") 