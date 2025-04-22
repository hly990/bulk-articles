# YT-Article Craft 插件系统设计

## 1. 概述

插件系统是YT-Article Craft应用的重要组成部分，它允许第三方开发者扩展应用功能，而无需修改核心代码。插件系统设计简单灵活，为未来的功能扩展提供了基础。

本文档详细说明了插件系统的设计和实现，包括：

- 插件接口设计
- 插件管理器设计
- 插件加载机制
- 插件通信机制
- 插件安全机制
- 示例插件实现

## 2. 插件接口设计

所有插件必须实现`PluginInterface`接口，该接口定义了插件的基本行为。

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class PluginInterface(ABC):
    """插件接口基类，所有插件必须实现这个接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @property
    def author(self) -> str:
        """插件作者"""
        return "Unknown"
    
    @property
    def website(self) -> Optional[str]:
        """插件网站"""
        return None
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件
        
        Returns:
            bool: 是否成功初始化
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """关闭插件
        
        Returns:
            bool: 是否成功关闭
        """
        pass
    
    @abstractmethod
    def get_hooks(self) -> Dict[str, Any]:
        """获取插件钩子函数
        
        Returns:
            Dict[str, Any]: 钩子名称和函数的字典
        """
        pass
    
    def get_settings(self) -> Dict[str, Any]:
        """获取插件设置
        
        Returns:
            Dict[str, Any]: 设置字典
        """
        return {}
    
    def set_settings(self, settings: Dict[str, Any]) -> bool:
        """设置插件设置
        
        Args:
            settings: 设置字典
            
        Returns:
            bool: 是否成功设置
        """
        return True
    
    def get_dependencies(self) -> List[str]:
        """获取插件依赖
        
        Returns:
            List[str]: 依赖插件名称列表
        """
        return []
```

## 3. 插件管理器设计

插件管理器负责加载、管理和卸载插件。它是一个单例类，可以通过`PluginManager.instance()`获取实例。

```python
import os
import importlib
import logging
import json
from typing import Dict, List, Type, Optional, Any, Callable

from .plugin_interface import PluginInterface


class PluginManager:
    """插件管理器，负责加载、管理和卸载插件"""
    
    _instance = None
    
    @classmethod
    def instance(cls) -> 'PluginManager':
        """获取插件管理器单例"""
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance
    
    def __init__(self):
        """初始化插件管理器"""
        self.plugins = {}  # 已加载的插件
        self.hooks = {}    # 注册的钩子
        self.plugin_dirs = ["plugins"]  # 插件目录
        self.disabled_plugins = []  # 禁用的插件
        self.settings_file = "data/plugin_settings.json"  # 插件设置文件
        
        # 加载插件设置
        self._load_settings()
    
    def discover_plugins(self) -> Dict[str, Type[PluginInterface]]:
        """发现可用的插件"""
        discovered_plugins = {}
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
                
            # 遍历插件目录
            for item in os.listdir(plugin_dir):
                if item.startswith("__"):
                    continue
                    
                # 检查是否是目录或Python文件
                item_path = os.path.join(plugin_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否是Python包
                    if os.path.exists(os.path.join(item_path, "__init__.py")):
                        self._load_plugin_package(item, discovered_plugins)
                elif item.endswith(".py"):
                    # 导入Python文件
                    self._load_plugin_module(item[:-3], item_path, discovered_plugins)
        
        return discovered_plugins
    
    def load_plugin(self, plugin_class: Type[PluginInterface]) -> bool:
        """加载单个插件"""
        try:
            # 创建插件实例
            plugin = plugin_class()
            
            # 检查插件是否被禁用
            if plugin.name in self.disabled_plugins:
                logging.info(f"插件 '{plugin.name}' 已被禁用，跳过加载")
                return False
            
            # 检查依赖
            for dependency in plugin.get_dependencies():
                if dependency not in self.plugins:
                    logging.error(f"插件 '{plugin.name}' 依赖 '{dependency}' 未加载")
                    return False
            
            # 初始化插件
            if not plugin.initialize():
                logging.error(f"插件 '{plugin.name}' 初始化失败")
                return False
            
            # 注册插件
            self.plugins[plugin.name] = plugin
            
            # 注册钩子
            for hook_name, hook_func in plugin.get_hooks().items():
                if hook_name not in self.hooks:
                    self.hooks[hook_name] = []
                self.hooks[hook_name].append(hook_func)
            
            logging.info(f"插件 '{plugin.name}' v{plugin.version} 加载成功")
            return True
            
        except Exception as e:
            logging.error(f"加载插件失败: {e}")
            return False
    
    def load_all_plugins(self) -> int:
        """加载所有插件"""
        discovered_plugins = self.discover_plugins()
        loaded_count = 0
        
        for plugin_name, plugin_class in discovered_plugins.items():
            if self.load_plugin(plugin_class):
                loaded_count += 1
        
        return loaded_count
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name not in self.plugins:
            return False
        
        plugin = self.plugins[plugin_name]
        
        try:
            # 关闭插件
            if not plugin.shutdown():
                logging.error(f"插件 '{plugin_name}' 关闭失败")
                return False
            
            # 移除钩子
            for hook_name, hook_funcs in self.hooks.items():
                self.hooks[hook_name] = [f for f in hook_funcs 
                                        if f not in plugin.get_hooks().values()]
            
            # 移除插件
            del self.plugins[plugin_name]
            
            logging.info(f"插件 '{plugin_name}' 卸载成功")
            return True
            
        except Exception as e:
            logging.error(f"卸载插件 '{plugin_name}' 失败: {e}")
            return False
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """调用钩子函数"""
        results = []
        
        if hook_name in self.hooks:
            for hook_func in self.hooks[hook_name]:
                try:
                    result = hook_func(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logging.error(f"调用钩子 '{hook_name}' 失败: {e}")
        
        return results
    
    def _load_settings(self) -> None:
        """加载插件设置"""
        self.plugin_settings = {}
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.plugin_settings = settings.get("plugins", {})
                    self.disabled_plugins = settings.get("disabled", [])
        except Exception as e:
            logging.error(f"加载插件设置失败: {e}")
```

## 4. 插件加载机制

插件加载机制包括以下步骤：

1. 发现可用插件
2. 检查插件依赖
3. 初始化插件
4. 注册插件钩子
5. 加载插件设置

插件可以从以下位置加载：

- 内置插件目录（plugins/builtin/）
- 用户插件目录（plugins/）
- 自定义插件目录

## 5. 插件通信机制

插件通信主要通过钩子（Hook）机制实现。钩子是一种回调函数，允许插件在特定事件发生时执行自定义代码。

### 5.1 钩子类型

系统预定义了以下钩子类型：

1. **应用钩子**：与应用程序生命周期相关的钩子
   - `app_started`: 应用程序启动时调用
   - `app_closing`: 应用程序关闭时调用

2. **任务钩子**：与视频任务相关的钩子
   - `task_created`: 创建任务时调用
   - `task_updated`: 更新任务时调用
   - `task_deleted`: 删除任务时调用
   - `before_process_video`: 处理视频前调用
   - `after_process_video`: 处理视频后调用

3. **UI钩子**：与用户界面相关的钩子
   - `main_window_created`: 主窗口创建时调用
   - `editor_context_menu`: 编辑器上下文菜单显示时调用
   - `preview_updated`: 预览更新时调用

4. **服务钩子**：与服务相关的钩子
   - `before_transcribe`: 转写前调用
   - `after_transcribe`: 转写后调用
   - `before_generate_article`: 生成文章前调用
   - `after_generate_article`: 生成文章后调用
   - `before_publish`: 发布前调用
   - `after_publish`: 发布后调用

### 5.2 注册钩子

插件通过`get_hooks`方法注册钩子：

```python
def get_hooks(self) -> Dict[str, Any]:
    return {
        "app_started": self.on_app_started,
        "task_created": self.on_task_created,
        "before_process_video": self.on_before_process_video
    }
```

### 5.3 调用钩子

应用程序通过`PluginManager.call_hook`方法调用钩子：

```python
# 调用应用启动钩子
PluginManager.instance().call_hook("app_started")

# 调用任务创建钩子，传递任务ID和标题
PluginManager.instance().call_hook("task_created", task_id, task_title)

# 调用处理视频前钩子，传递任务对象，并获取返回值
results = PluginManager.instance().call_hook("before_process_video", task)
```

## 6. 插件安全机制

为了确保插件不会对系统造成损害，插件系统实现了以下安全机制：

1. **沙箱执行**：插件在受限的环境中执行，无法访问系统关键资源
2. **权限控制**：插件只能通过预定义的接口访问应用功能
3. **异常处理**：插件抛出的异常不会影响主应用程序
4. **插件验证**：加载前验证插件的完整性和兼容性
5. **用户确认**：安装第三方插件前需要用户确认

## 7. 示例插件实现

### 7.1 自动翻译插件

```python
from typing import Dict, Any
from plugins.plugin_interface import PluginInterface
from services.translator import TranslatorService


class AutoTranslatePlugin(PluginInterface):
    """自动翻译插件，在生成文章后自动翻译为目标语言"""
    
    @property
    def name(self) -> str:
        return "auto_translate"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "在生成文章后自动翻译为目标语言"
    
    @property
    def author(self) -> str:
        return "YT-Article Craft Team"
    
    def initialize(self) -> bool:
        self.translator = TranslatorService()
        self.settings = {
            "target_language": "zh",  # 默认翻译为中文
            "auto_translate": True    # 默认启用自动翻译
        }
        return True
    
    def shutdown(self) -> bool:
        return True
    
    def get_hooks(self) -> Dict[str, Any]:
        return {
            "after_generate_article": self.on_after_generate_article
        }
    
    def get_settings(self) -> Dict[str, Any]:
        return self.settings
    
    def set_settings(self, settings: Dict[str, Any]) -> bool:
        self.settings.update(settings)
        return True
    
    def on_after_generate_article(self, task):
        """文章生成后的钩子函数"""
        if not self.settings["auto_translate"] or not task.article:
            return
        
        try:
            # 获取目标语言
            target_language = self.settings["target_language"]
            
            # 如果文章已经是目标语言，则跳过
            if task.language == target_language:
                return
            
            # 翻译文章标题
            translated_title = self.translator.translate(
                task.article.title, 
                source_language=task.language,
                target_language=target_language
            )
            
            # 翻译文章内容
            translated_content = self.translator.translate(
                task.article.content,
                source_language=task.language,
                target_language=target_language
            )
            
            # 更新文章
            task.article.title = translated_title
            task.article.content = translated_content
            task.language = target_language
            
        except Exception as e:
            logging.error(f"自动翻译失败: {e}")
```

### 7.2 SEO优化插件

```python
from typing import Dict, Any
import re
from plugins.plugin_interface import PluginInterface


class SEOOptimizerPlugin(PluginInterface):
    """SEO优化插件，优化文章以提高搜索引擎排名"""
    
    @property
    def name(self) -> str:
        return "seo_optimizer"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "优化文章以提高搜索引擎排名"
    
    @property
    def author(self) -> str:
        return "YT-Article Craft Team"
    
    def initialize(self) -> bool:
        self.settings = {
            "enabled": True,
            "min_keyword_density": 1.0,  # 最小关键词密度（%）
            "max_keyword_density": 3.0,  # 最大关键词密度（%）
            "add_meta_tags": True,       # 添加元标签
            "optimize_headings": True    # 优化标题
        }
        return True
    
    def shutdown(self) -> bool:
        return True
    
    def get_hooks(self) -> Dict[str, Any]:
        return {
            "before_publish": self.on_before_publish
        }
    
    def get_settings(self) -> Dict[str, Any]:
        return self.settings
    
    def set_settings(self, settings: Dict[str, Any]) -> bool:
        self.settings.update(settings)
        return True
    
    def on_before_publish(self, task, platform):
        """发布前的钩子函数"""
        if not self.settings["enabled"] or not task.article:
            return
        
        try:
            # 提取关键词
            keywords = self._extract_keywords(task.article.title, task.article.content)
            
            # 优化内容
            optimized_content = task.article.content
            
            # 优化标题
            if self.settings["optimize_headings"]:
                optimized_content = self._optimize_headings(optimized_content, keywords)
            
            # 添加元标签
            if self.settings["add_meta_tags"] and platform == "wordpress":
                meta_tags = self._generate_meta_tags(task.article.title, keywords)
                optimized_content = meta_tags + optimized_content
            
            # 更新文章内容
            task.article.content = optimized_content
            
        except Exception as e:
            logging.error(f"SEO优化失败: {e}")
    
    def _extract_keywords(self, title, content):
        """提取关键词"""
        # 简单实现，实际应用中可以使用更复杂的算法
        words = re.findall(r'\b\w+\b', title.lower() + " " + content.lower())
        word_count = {}
        
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_count[word] = word_count.get(word, 0) + 1
        
        # 按出现频率排序
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前5个关键词
        return [word for word, count in sorted_words[:5]]
```

## 8. 总结

YT-Article Craft的插件系统提供了一种灵活的方式来扩展应用功能，而无需修改核心代码。通过定义清晰的插件接口和钩子机制，第三方开发者可以轻松地开发和分享插件，从而丰富应用的功能。

插件系统的主要优点包括：

1. **模块化设计**：插件可以独立开发和部署
2. **灵活性**：用户可以根据需要启用或禁用插件
3. **可扩展性**：应用功能可以通过插件不断扩展
4. **安全性**：插件在受限环境中执行，不会影响系统安全

在未来的版本中，插件系统将进一步完善，增加更多的钩子点和API，以支持更丰富的插件功能。
