import logging, time
from PyQt6.QtCore import QCoreApplication, QTimer
from src.services.video_downloader import (
    VideoDownloader,
    DownloadError,
    NetworkError,
    InvalidURLError,
)

logging.basicConfig(level=logging.INFO)
app = QCoreApplication([])

"""
用例 1 ───────────────────────────────────────
无效 URL → InvalidURLError，立即失败
"""
vd1 = VideoDownloader(max_retries=2, timeout=30)

def on_err1(task, msg):
    print("\n[Case‑1] Error signal:", msg)
    assert isinstance(task.error, str) and "Invalid" in task.error
    QTimer.singleShot(0, app.quit)

vd1.download_error.connect(on_err1)
try:
    vd1.enqueue("https://notyoutube.com/foo")
except ValueError as e:
    print("[Case‑1] Caught expected error:", e)
    QTimer.singleShot(0, app.quit)     # 立刻触发 InvalidURLError

app.exec()   # ————————————————————————————

"""
用例 2 ───────────────────────────────────────
网络超时 → NetworkError + 重试
做法：把 timeout 降到 5 s，并下载一个超大视频；
在 1 次重试后仍超时，最终失败。
"""
app = QCoreApplication([])
vd2 = VideoDownloader(max_retries=2, timeout=5)   # 故意超短

def on_err2(task, msg):
    print("\n[Case‑2] Error signal:", msg)
    assert "timed out" in msg.lower()
    QTimer.singleShot(0, app.quit)

vd2.download_error.connect(on_err2)
# 随便一个视频；5 秒必定超时
vd2.enqueue("https://youtu.be/dQw4w9WgXcQ")

app.exec()   # ————————————————————————————

print("✅  2.7 错误处理测试全部通过")