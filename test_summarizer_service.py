#!/usr/bin/env python
"""
测试脚本 - 文章生成服务 (Task 4.5)

此脚本测试 src/services/summarizer_service.py 中的功能，包括：
- 基本的文章生成功能
- 处理多个转录文本段落
- 使用不同模板生成不同风格的文章
- 错误处理和任务取消
"""

import unittest
from unittest.mock import MagicMock, patch
import logging
import tempfile
import os
import threading
import time
from typing import Dict, Any, List

from src.models.template import Template
from src.services.deepseek_service import DeepSeekService
from src.services.prompt_templates import PromptAssembler
from src.services.transcript_segmenter import TranscriptSegmenter, Segment, SegmentManager
from src.services.summarizer_service import (
    SummarizerService, 
    SummarizerConfig, 
    SummarizerResult,
    SummarizationStatus,
    GenerationMetrics
)


class TestSummarizerService(unittest.TestCase):
    """测试SummarizerService的核心功能"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟的依赖服务
        self.mock_deepseek = MagicMock(spec=DeepSeekService)
        self.mock_prompt_assembler = MagicMock(spec=PromptAssembler)
        self.mock_segmenter = MagicMock(spec=TranscriptSegmenter)
        
        # 配置日志
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("test_summarizer")
        
        # 创建SummarizerService实例
        self.service = SummarizerService(
            deepseek_service=self.mock_deepseek,
            prompt_assembler=self.mock_prompt_assembler,
            segmenter=self.mock_segmenter,
            logger=self.logger
        )
        
        # 设置测试模板
        self.template = Template(
            name="Test Template",
            tone="professional",
            cta="联系我们了解更多信息",
            brand="专业、简洁、权威的声音"
        )
        
        # 设置测试文本
        self.test_transcript = """
        这是一段测试转录文本，用于测试SummarizerService的基本功能。
        它包含多个句子，可以被分割成不同的段落。
        这样可以测试服务处理多个段落的能力。
        """
        
        # 为DeepSeek服务设置模拟响应
        self.mock_deepseek.chat_completion.return_value = """# 测试文章标题

这是生成的文章内容。这个内容是由模拟的DeepSeek API返回的。

## 第一部分

这是文章的第一部分内容。它展示了如何从视频转录中生成结构化的文章。

## 第二部分

这是第二部分内容，继续探讨主题的其他方面。
"""
        
        # 设置模拟的段落管理器
        segment1 = Segment(
            text="这是第一个段落内容。",
            segment_id=1,
            total_segments=2,
            start_pos=0,
            end_pos=50,
            token_count=10
        )
        segment2 = Segment(
            text="这是第二个段落内容，将被合并成一篇完整的文章。",
            segment_id=2,
            total_segments=2,
            start_pos=51,
            end_pos=100,
            token_count=15,
            overlap_before=5
        )
        
        self.segments = [segment1, segment2]
        self.mock_segment_manager = MagicMock(spec=SegmentManager)
        self.mock_segment_manager.__len__.return_value = len(self.segments)
        self.mock_segment_manager.__iter__.return_value = iter(self.segments)
        self.mock_segment_manager.__getitem__.side_effect = lambda idx: self.segments[idx]
        
        # 设置分段器返回模拟段落管理器
        self.mock_segmenter.segment_transcript.return_value = self.mock_segment_manager
        
        # 设置prompt_assembler返回示例提示文本
        self.mock_prompt_assembler.build_prompt.return_value = """
        生成一篇专业风格的文章，基于以下转录文本:
        
        [转录文本内容]
        
        使用专业的语气和明确的标题。
        """
    
    def test_basic_article_generation(self):
        """测试基本的文章生成流程"""
        # 设置进度回调
        progress_updates = []
        
        def progress_callback(progress: float, message: str):
            progress_updates.append((progress, message))
        
        # 生成文章
        result = self.service.generate_article(
            transcript=self.test_transcript,
            template=self.template,
            job_id="test-job-1",
            progress_callback=progress_callback
        )
        
        # 验证结果
        self.assertEqual(result.status, SummarizationStatus.COMPLETED)
        self.assertIsNotNone(result.article_text)
        self.assertIsNotNone(result.title)
        self.assertEqual(result.template_id, self.template.id)
        
        # 验证服务调用
        self.mock_segmenter.segment_transcript.assert_called_once()
        self.assertEqual(self.mock_prompt_assembler.build_prompt.call_count, 2)  # 每个段落一次
        self.assertEqual(self.mock_deepseek.chat_completion.call_count, 2)  # 每个段落一次
        
        # 验证进度回调至少被调用3次
        self.assertGreaterEqual(len(progress_updates), 3)
        # 验证最终进度接近100%
        self.assertGreaterEqual(progress_updates[-1][0], 0.9)
    
    def test_empty_transcript(self):
        """测试空转录文本的处理"""
        # 配置segment_manager为空
        empty_manager = MagicMock(spec=SegmentManager)
        empty_manager.__len__.return_value = 0
        self.mock_segmenter.segment_transcript.return_value = empty_manager
        
        # 生成文章
        result = self.service.generate_article(
            transcript="",
            template=self.template
        )
        
        # 验证结果
        self.assertEqual(result.status, SummarizationStatus.FAILED)
        self.assertEqual(result.article_text, "")
        self.assertEqual(result.title, "")
        self.assertIsNotNone(result.error_message)
    
    def test_api_error_handling(self):
        """测试API错误处理"""
        from src.services.deepseek_service import APIResponseError
        
        # 配置DeepSeek服务抛出异常
        self.mock_deepseek.chat_completion.side_effect = APIResponseError("测试错误")
        
        # 生成文章
        result = self.service.generate_article(
            transcript=self.test_transcript,
            template=self.template
        )
        
        # 验证结果
        self.assertEqual(result.status, SummarizationStatus.FAILED)
        self.assertEqual(result.article_text, "")
        self.assertEqual(result.title, "")
        self.assertIn("DeepSeek API error", result.error_message)
    
    def test_job_cancellation(self):
        """测试任务取消功能"""
        job_id = "test-job-2"
        
        # 保存原始方法
        original_is_job_cancelled = self.service.is_job_cancelled
        
        # 覆盖is_job_cancelled方法以模拟已取消的任务
        def mock_is_job_cancelled(check_job_id):
            if check_job_id == job_id:
                return True
            return original_is_job_cancelled(check_job_id)
            
        try:
            # 应用mock
            self.service.is_job_cancelled = mock_is_job_cancelled
            
            # 生成文章
            result = self.service.generate_article(
                transcript=self.test_transcript,
                template=self.template,
                job_id=job_id
            )
            
            # 验证任务是否成功取消
            self.assertEqual(result.status, SummarizationStatus.CANCELLED)
            self.assertEqual(result.article_text, "")
            self.assertEqual(result.title, "")
        finally:
            # 恢复原始方法
            self.service.is_job_cancelled = original_is_job_cancelled
    
    def test_explicit_cancellation(self):
        """测试显式取消任务"""
        # 创建一个长时间运行的作业
        job_id = "test-job-3"
        
        # 开始取消操作
        result = self.service.cancel_job(job_id)
        self.assertFalse(result)  # 作业不存在，返回False
        
        # 模拟作业存在的情况
        self.service._cancellation_flags[job_id] = False
        result = self.service.cancel_job(job_id)
        self.assertTrue(result)  # 作业存在，返回True
        self.assertTrue(self.service._cancellation_flags[job_id])  # 标记已设置
    
    def test_thread_safety(self):
        """测试并发访问取消标志的线程安全性"""
        job_ids = [f"thread-job-{i}" for i in range(10)]
        results = {job_id: None for job_id in job_ids}
        
        def worker(job_id):
            # 注册任务
            with self.service._lock:
                self.service._cancellation_flags[job_id] = False
            # 取消任务
            result = self.service.cancel_job(job_id)
            # 存储结果
            results[job_id] = result
            # 验证标志
            self.assertTrue(self.service._cancellation_flags[job_id])
            # 清理
            with self.service._lock:
                del self.service._cancellation_flags[job_id]
        
        # 创建并启动线程
        threads = [threading.Thread(target=worker, args=(job_id,)) for job_id in job_ids]
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有操作是否成功
        for job_id, result in results.items():
            self.assertTrue(result)
        
        # 验证所有标志是否已清理
        self.assertEqual(len(self.service._cancellation_flags), 0)

    def test_is_job_cancelled(self):
        """测试is_job_cancelled方法"""
        # 测试作业不存在的情况
        self.assertFalse(self.service.is_job_cancelled("nonexistent-job"))
        
        # 测试作业存在但未取消的情况
        job_id = "test-job-uncancelled"
        with self.service._lock:
            self.service._cancellation_flags[job_id] = False
        self.assertFalse(self.service.is_job_cancelled(job_id))
        
        # 测试作业存在且已取消的情况
        job_id = "test-job-cancelled"
        with self.service._lock:
            self.service._cancellation_flags[job_id] = True
        self.assertTrue(self.service.is_job_cancelled(job_id))
        
        # 测试job_id为None的情况
        self.assertFalse(self.service.is_job_cancelled(None))

    def test_cancellation_during_api_call(self):
        """测试API调用期间的取消操作"""
        job_id = "test-job-api-cancel"
        
        # 模拟DeepSeekService模拟长时间API调用
        original_chat_completion = self.mock_deepseek.chat_completion
        
        def mock_chat_completion(*args, **kwargs):
            # 在"API调用"进行时设置取消标志
            self.service.cancel_job(job_id)
            # 模拟延迟
            time.sleep(0.1)
            return "模拟响应"
        
        try:
            # 替换为模拟方法
            self.mock_deepseek.chat_completion = mock_chat_completion
            
            # 生成文章，应该在第一个段落处理期间被取消
            result = self.service.generate_article(
                transcript=self.test_transcript,
                template=self.template,
                job_id=job_id
            )
            
            # 验证文章是否已取消
            self.assertEqual(result.status, SummarizationStatus.CANCELLED)
            
        finally:
            # 恢复原始方法
            self.mock_deepseek.chat_completion = original_chat_completion

    def test_partial_results_on_cancellation(self):
        """测试任务取消时的部分结果返回"""
        job_id = "test-job-partial"
        
        # 准备包含多个段落的转录文本
        long_transcript = self.test_transcript * 3  # 创建更长的转录文本
        
        # 模拟process_single_segment处理第一个段落后取消
        original_process_single_segment = self.service._process_single_segment
        processed_count = [0]  # 使用列表允许在嵌套函数中修改
        
        def mock_process_single_segment(segment, template, extra_instructions, context, job_id=None):
            processed_count[0] += 1
            
            # 正常处理第一个段落
            result = original_process_single_segment(segment, template, extra_instructions, context, job_id)
            
            # 第一个段落处理后，取消任务
            if processed_count[0] == 1:
                self.service.cancel_job(job_id)
                
            return result
        
        try:
            # 替换为模拟方法
            self.service._process_single_segment = mock_process_single_segment
            
            # 生成文章，应该在第一个段落后被取消
            result = self.service.generate_article(
                transcript=long_transcript,
                template=self.template,
                job_id=job_id
            )
            
            # 验证部分结果
            self.assertEqual(result.status, SummarizationStatus.CANCELLED)
            self.assertGreater(len(result.article_text), 0)  # 应该有内容
            self.assertIn("partial results", result.error_message.lower())
            
        finally:
            # 恢复原始方法
            self.service._process_single_segment = original_process_single_segment


if __name__ == "__main__":
    unittest.main() 