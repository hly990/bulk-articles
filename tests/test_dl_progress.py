import sys, logging, time
from PyQt6.QtCore import QCoreApplication, QTimer

logging.basicConfig(level=logging.INFO)

from src.services.video_downloader import (
    VideoDownloader,
    DownloadState,
    DownloadProgress,
)

app = QCoreApplication(sys.argv)
downloader = VideoDownloader()

# ---------- 信号回调 ----------
def on_state(task):
    print(f"[STATE] {task.url} -> {task.state.name}")

def on_progress(task, prog: DownloadProgress):
    print(f"[PROGRESS] {prog.percent:6.2f}%  {prog.speed}  ETA {prog.eta}", end="\r")

def on_done(task):
    print(f"\n[✓] Completed: {task.output_path}")
    QTimer.singleShot(0, app.quit)   # 退出事件循环

def on_error(task, msg):
    print(f"\n[✗] Failed: {msg}")
    QTimer.singleShot(0, app.quit)

downloader.state_changed.connect(on_state)
downloader.progress_changed.connect(on_progress)
downloader.download_completed.connect(on_done)
downloader.download_error.connect(on_error)

# ---------- 开始下载 ----------
task = downloader.enqueue("https://youtu.be/dQw4w9WgXcQ", quality="worstaudio")

# 如果 3 分钟还没结束就强制退出
QTimer.singleShot(180_000, app.quit)

# ---------- 执行 Qt 事件循环 ----------
app.exec()

downloader.shutdown()