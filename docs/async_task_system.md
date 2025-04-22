# YT-Article Craft 异步任务系统设计

## 1. 概述

在YT-Article Craft应用中，视频处理、转写、关键帧提取等操作都是耗时的任务，如果在主线程中执行这些操作，会导致UI阻塞，影响用户体验。因此，我们需要设计一个可扩展的异步任务系统，能够处理多个并发任务，并且能够优雅地处理取消操作。

## 2. 系统架构

异步任务系统的核心组件包括：

1. **TaskManager**：任务管理器，负责创建、调度和管理任务
2. **Task**：任务基类，定义任务的基本接口
3. **Worker**：工作线程，负责执行任务
4. **TaskQueue**：任务队列，管理待执行的任务

## 3. 核心组件设计

### 3.1 Task 基类

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class TaskStatus(Enum):
    PENDING = 0    # 等待执行
    RUNNING = 1    # 正在执行
    COMPLETED = 2  # 已完成
    FAILED = 3     # 失败
    CANCELED = 4   # 已取消

class Task(QObject, ABC):
    # 信号定义
    started = pyqtSignal()                      # 任务开始信号
    progress_changed = pyqtSignal(int, str)     # 进度变化信号 (百分比, 描述)
    completed = pyqtSignal(object)              # 任务完成信号 (结果)
    failed = pyqtSignal(str, Exception)         # 任务失败信号 (错误消息, 异常对象)
    canceled = pyqtSignal()                     # 任务取消信号
    
    def __init__(self, task_id: str, name: str, params: Dict[str, Any] = None):
        super().__init__()
        self._id = task_id
        self._name = name
        self._params = params or {}
        self._status = TaskStatus.PENDING
        self._progress = 0
        self._result = None
        self._error = None
        self._cancel_requested = False
    
    def request_cancel(self) -> None:
        """请求取消任务"""
        self._cancel_requested = True
    
    def is_cancel_requested(self) -> bool:
        """检查是否请求取消任务"""
        return self._cancel_requested
    
    @abstractmethod
    def run(self) -> Any:
        """执行任务，子类必须实现此方法"""
        pass
    
    def execute(self) -> None:
        """执行任务的包装方法，处理状态变化和异常"""
        try:
            if self._cancel_requested:
                self._status = TaskStatus.CANCELED
                self.canceled.emit()
                return
            
            self._status = TaskStatus.RUNNING
            self.started.emit()
            
            # 执行实际任务
            result = self.run()
            
            if self._cancel_requested:
                self._status = TaskStatus.CANCELED
                self.canceled.emit()
            else:
                self._result = result
                self._status = TaskStatus.COMPLETED
                self.completed.emit(result)
                
        except Exception as e:
            self._error = e
            self._status = TaskStatus.FAILED
            self.failed.emit(str(e), e)
```

### 3.2 Worker 类

```python
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

class WorkerSignals(QObject):
    """工作线程信号"""
    finished = pyqtSignal()
    error = pyqtSignal(str, Exception)

class Worker(QRunnable):
    """工作线程，用于执行任务"""
    
    def __init__(self, task: Task):
        super().__init__()
        self.task = task
        self.signals = WorkerSignals()
        self.setAutoDelete(True)
    
    @pyqtSlot()
    def run(self):
        """执行任务"""
        try:
            self.task.execute()
        except Exception as e:
            self.signals.error.emit(str(e), e)
        finally:
            self.signals.finished.emit()
```

### 3.3 TaskManager 类

```python
import uuid
from typing import Dict, List, Type, Optional
from PyQt6.QtCore import QObject, QThreadPool

class TaskManager(QObject):
    """任务管理器，负责创建、调度和管理任务"""
    
    _instance = None
    
    @classmethod
    def instance(cls) -> 'TaskManager':
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self._thread_pool = QThreadPool.globalInstance()
        self._tasks: Dict[str, Task] = {}
        self._task_types: Dict[str, Type[Task]] = {}
        
        # 设置最大线程数
        max_threads = min(8, QThreadPool.globalInstance().maxThreadCount())
        self._thread_pool.setMaxThreadCount(max_threads)
    
    def register_task_type(self, task_type: str, task_class: Type[Task]) -> None:
        """注册任务类型"""
        self._task_types[task_type] = task_class
    
    def create_task(self, task_type: str, name: str, params: Dict[str, any] = None) -> Optional[Task]:
        """创建任务"""
        if task_type not in self._task_types:
            return None
        
        task_id = str(uuid.uuid4())
        task_class = self._task_types[task_type]
        task = task_class(task_id, name, params)
        self._tasks[task_id] = task
        
        return task
    
    def submit_task(self, task: Task) -> str:
        """提交任务执行"""
        if task.id not in self._tasks:
            self._tasks[task.id] = task
        
        worker = Worker(task)
        self._thread_pool.start(worker)
        
        return task.id
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.request_cancel()
            return True
        return False
```

## 4. 视频处理任务示例

```python
import time
from typing import Any, Dict, List

class VideoProcessTask(Task):
    """视频处理任务"""
    
    def __init__(self, task_id: str, name: str, params: Dict[str, Any] = None):
        super().__init__(task_id, name, params)
        
        if not params or 'url' not in params:
            raise ValueError("视频URL是必需的参数")
        
        self.url = params['url']
        self.language = params.get('language', 'en')
        self.output_dir = params.get('output_dir', './output')
    
    def run(self) -> Dict[str, Any]:
        """执行视频处理任务"""
        try:
            # 步骤1：下载视频 (25%)
            self.progress_changed.emit(0, "开始下载视频...")
            video_path = self._download_video()
            if self.is_cancel_requested():
                return None
            
            # 步骤2：转写视频 (50%)
            self.progress_changed.emit(25, "开始转写视频...")
            transcript = self._transcribe_video()
            if self.is_cancel_requested():
                return None
            
            # 步骤3：提取关键帧 (75%)
            self.progress_changed.emit(50, "开始提取关键帧...")
            keyframes = self._extract_keyframes()
            if self.is_cancel_requested():
                return None
            
            # 步骤4：生成摘要 (100%)
            self.progress_changed.emit(75, "开始生成摘要...")
            summary = self._generate_summary()
            if self.is_cancel_requested():
                return None
            
            self.progress_changed.emit(100, "处理完成")
            
            # 返回处理结果
            return {
                'video_path': video_path,
                'transcript': transcript,
                'keyframes': keyframes,
                'summary': summary
            }
            
        except Exception as e:
            self.progress_changed.emit(0, f"处理失败: {str(e)}")
            raise
    
    def _download_video(self):
        # 模拟下载过程
        for i in range(25):
            if self.is_cancel_requested():
                return None
            time.sleep(0.1)
            self.progress_changed.emit(i, f"下载视频: {i}%")
        return "video.mp4"
    
    def _transcribe_video(self):
        # 模拟转写过程
        for i in range(25):
            if self.is_cancel_requested():
                return None
            time.sleep(0.1)
            self.progress_changed.emit(25 + i, f"转写视频: {i}%")
        return "视频转写文本"
    
    def _extract_keyframes(self):
        # 模拟关键帧提取
        frames = []
        for i in range(25):
            if self.is_cancel_requested():
                return frames
            time.sleep(0.1)
            self.progress_changed.emit(50 + i, f"提取关键帧: {i}%")
            frames.append(f"frame_{i}.jpg")
        return frames
    
    def _generate_summary(self):
        # 模拟摘要生成
        for i in range(25):
            if self.is_cancel_requested():
                return None
            time.sleep(0.1)
            self.progress_changed.emit(75 + i, f"生成摘要: {i}%")
        return "视频摘要文本"
```

## 5. 在UI中使用异步任务系统

```python
from PyQt6.QtWidgets import QMainWindow, QPushButton, QProgressBar, QLabel, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("YT-Article Craft")
        self.resize(800, 600)
        
        # 初始化任务管理器
        self.task_manager = TaskManager.instance()
        self.task_manager.register_task_type("video_process", VideoProcessTask)
        
        # 创建UI组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.start_button = QPushButton("开始处理")
        self.start_button.clicked.connect(self._on_start_clicked)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        self.status_label = QLabel("就绪")
        
        layout.addWidget(self.start_button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        # 当前任务ID
        self.current_task_id = None
    
    def _on_start_clicked(self):
        """开始按钮点击事件"""
        params = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'language': 'zh',
            'output_dir': './output'
        }
        
        task = self.task_manager.create_task("video_process", "处理视频", params)
        if task:
            task.started.connect(self._on_task_started)
            task.progress_changed.connect(self._on_task_progress)
            task.completed.connect(self._on_task_completed)
            task.failed.connect(self._on_task_failed)
            task.canceled.connect(self._on_task_canceled)
            
            self.current_task_id = self.task_manager.submit_task(task)
            
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("准备中...")
    
    def _on_cancel_clicked(self):
        """取消按钮点击事件"""
        if self.current_task_id:
            self.task_manager.cancel_task(self.current_task_id)
            self.status_label.setText("正在取消...")
            self.cancel_button.setEnabled(False)
    
    def _on_task_started(self):
        """任务开始事件"""
        self.status_label.setText("处理中...")
    
    def _on_task_progress(self, progress, description):
        """任务进度事件"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(description)
    
    def _on_task_completed(self, result):
        """任务完成事件"""
        self.progress_bar.setValue(100)
        self.status_label.setText("处理完成")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.current_task_id = None
    
    def _on_task_failed(self, error_message, exception):
        """任务失败事件"""
        self.progress_bar.setValue(0)
        self.status_label.setText(f"处理失败: {error_message}")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.current_task_id = None
    
    def _on_task_canceled(self):
        """任务取消事件"""
        self.progress_bar.setValue(0)
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.current_task_id = None
```

## 6. 多任务并发处理

```python
class TaskQueueManager(QObject):
    """任务队列管理器，用于管理多个任务的执行"""
    
    queue_started = pyqtSignal()                # 队列开始信号
    queue_completed = pyqtSignal()              # 队列完成信号
    queue_progress_changed = pyqtSignal(int)    # 队列进度变化信号 (百分比)
    
    def __init__(self, max_concurrent_tasks: int = 2):
        super().__init__()
        self.task_manager = TaskManager.instance()
        self.max_concurrent_tasks = max_concurrent_tasks
        
        self.pending_tasks = []    # 待执行的任务参数列表
        self.running_tasks = {}    # 正在执行的任务 {task_id: task}
        self.completed_tasks = {}  # 已完成的任务 {task_id: result}
        
        self.is_running = False
    
    def add_task(self, task_type: str, name: str, params: Dict[str, Any]) -> None:
        """添加任务到队列"""
        self.pending_tasks.append((task_type, name, params))
    
    def start_queue(self) -> None:
        """开始执行任务队列"""
        if self.is_running:
            return
        
        self.is_running = True
        self.queue_started.emit()
        
        # 启动初始任务
        self._start_next_tasks()
    
    def cancel_queue(self) -> None:
        """取消任务队列"""
        self.is_running = False
        
        # 取消所有正在运行的任务
        for task_id in list(self.running_tasks.keys()):
            self.task_manager.cancel_task(task_id)
        
        # 清空待执行任务
        self.pending_tasks.clear()
    
    def _start_next_tasks(self) -> None:
        """启动下一批任务"""
        if not self.is_running:
            return
        
        # 计算可以启动的任务数量
        available_slots = self.max_concurrent_tasks - len(self.running_tasks)
        
        # 启动任务
        for _ in range(min(available_slots, len(self.pending_tasks))):
            if not self.pending_tasks:
                break
            
            task_type, name, params = self.pending_tasks.pop(0)
            
            # 创建任务
            task = self.task_manager.create_task(task_type, name, params)
            if task:
                # 连接信号
                task.completed.connect(lambda result, tid=task.id: self._on_task_completed(tid, result))
                task.failed.connect(lambda msg, exc, tid=task.id: self._on_task_failed(tid, msg, exc))
                task.canceled.connect(lambda tid=task.id: self._on_task_canceled(tid))
                
                # 提交任务
                self.task_manager.submit_task(task)
                self.running_tasks[task.id] = task
```

## 7. 总结

通过以上设计，我们实现了一个可扩展的异步任务系统，具有以下特点：

1. 基于PyQt6的信号槽机制，实现了任务状态和进度的实时反馈
2. 支持任务取消，可以优雅地中断正在执行的任务
3. 支持多任务并发执行，提高处理效率
4. 模块化设计，便于扩展新的任务类型
5. 完善的错误处理机制，确保应用稳定性

这个异步任务系统将成为YT-Article Craft应用的核心组件，为用户提供流畅的使用体验。
