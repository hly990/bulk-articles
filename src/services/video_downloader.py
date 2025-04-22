from __future__ import annotations

"""Core video download service (task 2.4).

This first iteration focuses on *basic functionality*:
• Queue management (add / start / status)
• Actual download using :class:`YtDlpWrapper` → writes to :class:`MediaStorage`
• Simple state tracking (QUEUED → DOWNLOADING → COMPLETED / FAILED / CANCELLED)
• Stubs for pause / cancel (real implementation comes with task 2.5 / 2.8)

Progress tracking & Qt signals are **not** included yet – that will be covered
by task 2.5.
"""

from dataclasses import dataclass, field
import logging
import threading
from enum import Enum, auto
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Optional, List
import re
from PyQt6.QtCore import QObject, pyqtSignal
import signal
import time
import subprocess

from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError
from .media_storage import MediaStorage
from .youtube_utils import YouTubeValidator, MetadataExtractor, VideoFormat

__all__ = [
    "DownloadState",
    "DownloadTask",
    "VideoDownloader",
]


class DownloadState(Enum):
    """Simple enumeration of download states."""

    QUEUED = auto()
    DOWNLOADING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class DownloadTask:
    """Information tracked for each download job."""

    url: str
    quality: str = "best"
    state: DownloadState = DownloadState.QUEUED
    output_path: Optional[Path] = None
    error: Optional[str] = None
    video_id: Optional[str] = None

    # internal use
    _thread: Optional[threading.Thread] = field(default=None, repr=False, compare=False)


# ------------------------------------------------------------------
# Progress data structure
# ------------------------------------------------------------------


@dataclass
class DownloadProgress:
    """Structured progress information parsed from yt‑dlp output."""

    percent: float  # 0‑100
    speed: str  # e.g. "1.23MiB/s"
    eta: str  # e.g. "00:12"


# Regex to parse yt-dlp progress lines, tolerate both CR and LF endings
_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<percent>\d+\.\d+)%.*?of.*?at\s+(?P<speed>[\d\.A-Za-z/]+)\s+ETA\s+(?P<eta>[\d:]+)",
    re.IGNORECASE,
)


# ------------------------------------------------------------------
# Error hierarchy (task 2.7)
# ------------------------------------------------------------------


class DownloadError(RuntimeError):
    """Base download error raised for non‑successful tasks."""


class NetworkError(DownloadError):
    """Network‑related issues, e.g. timeout, DNS, connection reset."""


class GeoRestrictionError(DownloadError):
    """Video unavailable in current region."""


class AgeRestrictionError(DownloadError):
    """Video requires age verification (not supported)."""


class InvalidURLError(DownloadError):
    """Provided URL is not recognised or invalid."""


class VideoDownloader(QObject):
    """Download manager implementing a simple FIFO queue with Qt signals."""

    # Qt signals
    progress_changed = pyqtSignal(DownloadTask, DownloadProgress)  # real‑time progress
    state_changed = pyqtSignal(DownloadTask)  # any state change
    download_completed = pyqtSignal(DownloadTask)
    download_error = pyqtSignal(DownloadTask, str)

    def __init__(
        self,
        *,
        wrapper: Optional[YtDlpWrapper] = None,
        storage: Optional[MediaStorage] = None,
        logger: Optional[logging.Logger] = None,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> None:
        super().__init__()  # QObject init

        self.logger = logger or logging.getLogger(__name__)
        self.wrapper = wrapper or YtDlpWrapper()
        self.storage = storage or MediaStorage()

        self._queue: "Queue[DownloadTask]" = Queue()
        self._active_task: Optional[DownloadTask] = None
        self._manager_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._stop_event = threading.Event()
        self._manager_thread.start()

        self._max_retries = max_retries
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enqueue(self, url: str, *, quality: str = "best") -> DownloadTask:
        if not YouTubeValidator.is_valid(url):
            raise ValueError("Invalid YouTube URL")

        task = DownloadTask(url=url, quality=quality)
        self._queue.put(task)
        self.logger.info("Enqueued download: %s", url)
        self.state_changed.emit(task)
        return task

    def list_tasks(self) -> List[DownloadTask]:
        tasks: List[DownloadTask] = []
        if self._active_task:
            tasks.append(self._active_task)
        tasks.extend(list(self._queue.queue))  # access underlying deque for snapshot
        return tasks

    def pause(self, task: DownloadTask) -> None:  # placeholder
        self.logger.warning("Pause not implemented yet for task: %s", task.url)

    def cancel(self, task: DownloadTask) -> None:  # placeholder
        if task.state in (DownloadState.COMPLETED, DownloadState.CANCELLED):
            return
        task.state = DownloadState.CANCELLED
        task.error = "Cancelled by user"
        # If it's the active download, signal stop (NYI)
        self.logger.info("Cancelled task: %s", task.url)
        self.state_changed.emit(task)

    def shutdown(self) -> None:
        """Gracefully stop background manager thread."""
        self._stop_event.set()
        self._manager_thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Internal – manager thread
    # ------------------------------------------------------------------
    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                task: DownloadTask = self._queue.get(timeout=0.5)
            except Empty:
                continue

            self._active_task = task
            self._perform_download(task)
            self._active_task = None
            self._queue.task_done()

    def _perform_download(self, task: DownloadTask) -> None:
        task.state = DownloadState.DOWNLOADING
        self.state_changed.emit(task)
        try:
            meta = MetadataExtractor(storage=self.storage, wrapper=self.wrapper).get_metadata(task.url)
            task.video_id = meta.video_id
            output_path = self._determine_output_path(meta, preferred_quality=task.quality)
            task.output_path = output_path
            self.logger.info("Downloading %s → %s", task.url, output_path)

            # Ensure parent dirs
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if not self._execute_download_cli(task, output_path):
                return  # task already updated inside helper

            task.state = DownloadState.COMPLETED
            self.logger.info("Download completed: %s", output_path)
            self.state_changed.emit(task)
            self.download_completed.emit(task)
        except Exception as exc:  # noqa: BLE001 – broad for robust logging
            self.logger.error("Download failed: %s", exc)
            task.state = DownloadState.FAILED
            task.error = str(exc)
            self.state_changed.emit(task)
            self.download_error.emit(task, task.error)
            return

    def _determine_output_path(self, meta: "VideoMetadata", *, preferred_quality: str) -> Path:  # noqa: D401
        # Try to choose extension based on quality/format id
        ext = "mp4"
        if "+" in preferred_quality:  # merged formats (id+id)
            ext = "mkv"
        else:
            # search format list for matching id
            for fmt in meta.formats:
                if fmt.get("format_id") == preferred_quality:
                    ext = fmt.get("ext", "mp4")
                    break
        return self.storage.get_video_path(meta.video_id, fmt=ext)

    # ------------------------------------------------------------------
    # CLI execution with real‑time progress parsing
    # ------------------------------------------------------------------

    def _execute_download_cli(self, task: DownloadTask, output_path: Path) -> bool:
        """Run yt‑dlp CLI and emit progress. Return *True* if success."""

        cmd_base = [
            "yt-dlp",
            "-f",
            task.quality,
            "-o",
            str(output_path),
            task.url,
        ]

        attempts = 0
        while attempts < self._max_retries:
            attempts += 1
            cmd = [*cmd_base]
            if attempts > 1:
                self.logger.info("Retrying download (attempt %d/%d)...", attempts, self._max_retries)

            self.logger.debug("Running CLI: %s", cmd)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # timeout watchdog
            try:
                return self._monitor_process(proc, task)
            except NetworkError as nerr:
                self.logger.warning("Transient network error: %s", nerr)
                if attempts < self._max_retries:
                    time.sleep(5)
                    continue
                task.error = str(nerr)
                task.state = DownloadState.FAILED
                self.state_changed.emit(task)
                self.download_error.emit(task, task.error)
                return False
            except DownloadError as derr:
                task.error = str(derr)
                task.state = DownloadState.FAILED
                self.state_changed.emit(task)
                self.download_error.emit(task, task.error)
                return False

        return False  # shouldn't reach

    # ------------------------------------------------------------------
    # Helper: monitor yt-dlp proc & parse output, with timeout
    # ------------------------------------------------------------------

    def _monitor_process(self, proc: "subprocess.Popen[str]", task: DownloadTask) -> bool:
        """Monitor *proc* for progress, enforce timeout and classify errors."""
        import select, time

        start_time = time.time()
        line_buffer = ""

        if proc.stdout is None:  # pragma: no cover
            raise NetworkError("yt-dlp stdout unavailable")

        while True:
            if time.time() - start_time > self._timeout:
                proc.kill()
                raise NetworkError("Download timed out")

            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if ready:
                raw_line = proc.stdout.readline()
                if not raw_line:
                    # EOF
                    if proc.poll() is not None:
                        break
                    continue
                line = raw_line.strip("\r\n")
                line_buffer += line + "\n"

                match = _PROGRESS_RE.search(line)
                if match:
                    progress = DownloadProgress(
                        percent=float(match.group("percent")),
                        speed=match.group("speed"),
                        eta=match.group("eta"),
                    )
                    self.progress_changed.emit(task, progress)

            if proc.poll() is not None:
                break

        proc.wait()

        if proc.returncode != 0:
            # classify
            err_cls = self._classify_error(line_buffer)
            raise err_cls(f"yt-dlp exited with code {proc.returncode}")

        return True

    # ------------------------------------------------------------------
    # Error classification helper
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_error(output: str) -> type[DownloadError]:
        txt = output.lower()
        if "proxy" in txt or "timed out" in txt or "connection" in txt or "http error" in txt:
            return NetworkError
        if "restricted" in txt and "geo" in txt:
            return GeoRestrictionError
        if "age" in txt and "restricted" in txt:
            return AgeRestrictionError
        return DownloadError

    # New helper ------------------------------------------------------
    def get_available_formats(self, url: str, *, use_cache: bool = True) -> list[VideoFormat]:
        """Expose format list via internal MetadataExtractor."""
        return MetadataExtractor(storage=self.storage, wrapper=self.wrapper).list_formats(url, use_cache=use_cache) 