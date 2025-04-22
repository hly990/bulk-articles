# YT-Article Craft 数据模型

本文档详细说明了YT-Article Craft应用程序的核心数据模型及其关系。

## 概述

YT-Article Craft应用程序的核心数据模型包括以下几个类：

1. **VideoTask**: 表示一个视频处理任务，包含视频URL、转写文本、关键帧和生成的文章等信息。
2. **Template**: 表示一个文章模板，包含风格、CTA、品牌语调等信息。
3. **Keyframe**: 表示视频的关键帧，包含时间戳、图片路径和说明文字等信息。
4. **Article**: 表示生成的文章，包含标题、内容和元数据等信息。

## 数据模型详细说明

### VideoTask 类

`VideoTask`是应用程序的核心数据模型，代表一个从YouTube视频生成文章的处理任务。

#### 主要属性

- `id`: 任务唯一标识符（UUID）
- `url`: YouTube视频URL
- `status`: 任务状态（等待执行、下载中、转写中、提取关键帧中、生成文章中、已完成、失败）
- `language`: 语言代码（默认为"en"）
- `title`: 视频标题
- `description`: 视频描述
- `transcript`: 转写文本
- `keyframes`: 关键帧列表（Keyframe对象）
- `article`: 生成的文章（Article对象）
- `template_id`: 使用的模板ID
- `created_at`: 创建时间戳
- `updated_at`: 更新时间戳
- `metadata`: 元数据字典

#### 主要方法

- `create_from_url(url, template_id=None, language="en")`: 从URL创建新任务
- `update_status(new_status)`: 更新任务状态
- `add_keyframe(keyframe)`: 添加关键帧
- `set_article(article)`: 设置文章
- `update_article(article_content)`: 更新文章内容
- `update_keyframes(keyframes)`: 更新关键帧列表
- `to_dict()`: 序列化为字典
- `to_json()`: 序列化为JSON字符串
- `save(directory=None)`: 保存到文件
- `from_dict(data)`: 从字典创建实例
- `from_json(json_str)`: 从JSON字符串创建实例
- `load(filepath)`: 从文件加载
- `list_saved_tasks(directory=None)`: 列出已保存的任务
- `clone()`: 创建任务副本
- `extract_video_id()`: 提取YouTube视频ID

### Template 类

`Template`类定义了文章的生成模板，包括风格、语调、结构等。

#### 主要属性

- `id`: 模板唯一标识符（UUID）
- `name`: 模板名称
- `tone`: 语调风格（专业、休闲、故事化、技术、教育）
- `cta`: Call to Action文本
- `brand`: 品牌语调描述
- `structure`: 文章结构（JSON格式）
- `css`: 自定义CSS样式
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `metadata`: 元数据字典

#### 主要方法

- `to_dict()`: 序列化为字典
- `to_json()`: 序列化为JSON字符串
- `from_dict(data)`: 从字典创建实例
- `from_json(json_str)`: 从JSON字符串创建实例
- `clone(new_name=None)`: 创建模板副本
- `create_default_templates()`: 创建默认模板集合

### Keyframe 类

`Keyframe`类表示视频中的关键帧，包含时间戳和图片信息。

#### 主要属性

- `timestamp`: 时间戳（HH:MM:SS格式）
- `image_path`: 图片文件路径
- `caption`: 图片说明文字
- `metadata`: 元数据字典

#### 主要方法

- `to_dict()`: 序列化为字典
- `from_dict(data)`: 从字典创建实例

### Article 类

`Article`类表示从视频生成的文章。

#### 主要属性

- `title`: 文章标题
- `content`: 文章内容（Markdown格式）
- `template_id`: 使用的模板ID
- `metadata`: 元数据字典

#### 主要方法

- `to_dict()`: 序列化为字典
- `from_dict(data)`: 从字典创建实例

## 数据模型关系

数据模型之间存在以下关系：

1. **VideoTask 与 Template**: VideoTask通过`template_id`引用Template。一个Task可以使用一个Template，一个Template可以被多个Task使用。

2. **VideoTask 与 Keyframe**: VideoTask包含多个Keyframe对象，存储在`keyframes`列表中。Keyframe属于特定的VideoTask。

3. **VideoTask 与 Article**: VideoTask包含一个Article对象，存储在`article`属性中。Article属于特定的VideoTask。

4. **Article 与 Template**: Article通过`template_id`引用Template。Article的结构和样式由Template决定。

## 序列化与持久化

所有数据模型都支持序列化为JSON格式以便持久化存储。主要通过以下方法实现：

1. `to_dict()`: 将对象转换为Python字典
2. `to_json()`: 将对象转换为JSON字符串
3. `from_dict(data)`: 从字典创建对象
4. `from_json(json_str)`: 从JSON字符串创建对象

VideoTask还提供了直接保存到文件系统和从文件系统加载的方法：

1. `save(directory=None)`: 将任务保存到JSON文件
2. `load(filepath)`: 从JSON文件加载任务

## 默认值与数据验证

所有数据模型都实现了合理的默认值和数据验证：

1. **VideoTask**: 验证YouTube URL格式和任务状态值
2. **Template**: 验证模板名称和语调值
3. **Keyframe**: 要求时间戳和图片路径
4. **Article**: 要求标题和内容

## 工厂方法

数据模型提供了以下工厂方法，方便创建新实例：

1. `VideoTask.create_from_url()`: 从YouTube URL创建新任务
2. `Template.create_default_templates()`: 创建预定义的默认模板集合 