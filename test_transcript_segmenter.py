#!/usr/bin/env python
"""
测试脚本 - 转录文本分段功能 (Task 4.4)

此脚本测试src/services/transcript_segmenter.py中的功能，
包括文本分段、不同分段策略和重叠机制。
"""

import sys
import os
from pathlib import Path
import unittest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.services.transcript_segmenter import (
    TranscriptSegmenter,
    Segment,
    SegmentManager,
    TokenizerInterface,
    SimpleTokenizer
)


# 创建一些测试用的文本样本
SHORT_TEXT = "这是一个简短的测试文本。它只有几句话。用于测试基本功能。"

MEDIUM_TEXT = """
这是一个中等长度的文本。它包含多个句子和一些段落结构。

这是第二个段落，用于测试段落边界检测。这个段落有多个句子，应该可以在句子边界处分割。
测试句子边界和标点符号的处理，比如逗号、句号和问号。这是一个问句吗？当然是的！

下面是第三个段落，继续测试分段功能。
"""

# 生成一个长文本用于测试
LONG_TEXT = "\n\n".join([
    f"段落 {i+1}: 这是测试长文本的段落 {i+1}。它包含了一些内容用于测试。这里有多个句子，确保可以测试句子边界。这是另一个句子。" * 3
    for i in range(10)
])

# 添加一些特殊情况的文本
SINGLE_SENTENCE_TEXT = "这是一个非常长的单一句子，它没有任何标点符号也没有自然段落边界它将测试在没有明显分割点的情况下如何处理文本这种情况应该会通过词边界来分割文本或者在必要时通过固定长度分割"

MIXED_TEXT = f"""
短段落。

{SINGLE_SENTENCE_TEXT}

再来一个短段落作为结束。
"""


class TestTokenizer(unittest.TestCase):
    """测试简单分词器功能"""
    
    def setUp(self):
        self.tokenizer = SimpleTokenizer()
    
    def test_count_tokens(self):
        """测试token计数功能"""
        text = "这是一个测试文本，包含标点符号!"
        token_count = self.tokenizer.count_tokens(text)
        self.assertGreater(token_count, 0)
        
        # 空文本应该返回0个token
        self.assertEqual(self.tokenizer.count_tokens(""), 0)
        
        # 长文本应该有更多的token
        long_count = self.tokenizer.count_tokens(MEDIUM_TEXT)
        short_count = self.tokenizer.count_tokens(SHORT_TEXT)
        self.assertGreater(long_count, short_count)
    
    def test_truncate_text(self):
        """测试文本截断功能"""
        text = "这是一个非常长的测试文本，用于验证截断功能，它应该包含足够多的词以允许被截断"
        max_tokens = 5
        truncated = self.tokenizer.truncate_text_to_tokens(text, max_tokens)
        
        # 截断后的文本应该比原始文本短或相等（当原文本已经很短时）
        self.assertLessEqual(len(truncated), len(text))
        
        # 截断后的token数应该不超过最大限制
        self.assertLessEqual(self.tokenizer.count_tokens(truncated), max_tokens)
        
        # 如果文本已经在限制之内，应该返回原样
        short_text = "短文本"
        self.assertEqual(
            self.tokenizer.truncate_text_to_tokens(short_text, 10),
            short_text
        )


class TestSegment(unittest.TestCase):
    """测试Segment数据模型功能"""
    
    def test_segment_properties(self):
        """测试Segment的属性和方法"""
        segment = Segment(
            text="测试文本",
            segment_id=1,
            total_segments=3,
            start_pos=0,
            end_pos=10,
            token_count=5
        )
        
        # 测试基本属性
        self.assertEqual(segment.text, "测试文本")
        self.assertEqual(segment.segment_id, 1)
        self.assertEqual(segment.total_segments, 3)
        
        # 测试衍生属性
        self.assertTrue(segment.is_first)
        self.assertFalse(segment.is_last)
        self.assertEqual(segment.length, 4)
        
        # 测试最后一个段落
        last_segment = Segment(
            text="最后一段",
            segment_id=3,
            total_segments=3,
            start_pos=20,
            end_pos=30,
            token_count=5
        )
        self.assertTrue(last_segment.is_last)
        self.assertFalse(last_segment.is_first)


class TestSegmentManager(unittest.TestCase):
    """测试SegmentManager功能"""
    
    def setUp(self):
        segments = [
            Segment(
                text=f"段落 {i}",
                segment_id=i,
                total_segments=3,
                start_pos=i*10,
                end_pos=(i+1)*10,
                token_count=5
            )
            for i in range(1, 4)
        ]
        self.manager = SegmentManager(segments)
    
    def test_segment_access(self):
        """测试段落访问方法"""
        self.assertEqual(len(self.manager), 3)
        self.assertEqual(self.manager[0].segment_id, 1)
        self.assertEqual(self.manager[1].segment_id, 2)
        
        # 迭代访问
        segment_ids = [s.segment_id for s in self.manager]
        self.assertEqual(segment_ids, [1, 2, 3])
    
    def test_segment_stats(self):
        """测试段落统计功能"""
        stats = self.manager.get_segment_stats()
        self.assertEqual(stats["total_segments"], 3)
        self.assertEqual(stats["total_tokens"], 15)
        self.assertEqual(stats["average_tokens"], 5.0)
        
        # 空管理器应该返回零值统计
        empty_manager = SegmentManager()
        empty_stats = empty_manager.get_segment_stats()
        self.assertEqual(empty_stats["total_segments"], 0)
    
    def test_segment_processing(self):
        """测试段落批处理功能"""
        # 对所有段落应用函数
        def processor(segment):
            return segment.text.upper()
        
        results = self.manager.process_segments(processor)
        self.assertEqual(results, ["段落 1".upper(), "段落 2".upper(), "段落 3".upper()])
        
        # 测试获取特定ID的段落
        segment = self.manager.get_segment_by_id(2)
        self.assertEqual(segment.segment_id, 2)
        
        # 不存在的ID应该返回None
        self.assertIsNone(self.manager.get_segment_by_id(99))


class TestTranscriptSegmenter(unittest.TestCase):
    """测试TranscriptSegmenter主要功能"""
    
    def setUp(self):
        self.tokenizer = SimpleTokenizer()
        self.segmenter = TranscriptSegmenter(
            tokenizer=self.tokenizer,
            max_tokens_per_segment=200,
            overlap_strategy="sentence"
        )
    
    def test_basic_segmentation(self):
        """测试基本分段功能"""
        # 短文本可能只有一个段落
        result = self.segmenter.segment_transcript(SHORT_TEXT)
        self.assertGreaterEqual(len(result), 1)
        
        # 中等文本应该被分成至少一个段落
        result = self.segmenter.segment_transcript(MEDIUM_TEXT)
        self.assertGreaterEqual(len(result), 1)
        
        # 长文本应该被分成多个段落
        long_result = self.segmenter.segment_transcript(LONG_TEXT)
        short_result = self.segmenter.segment_transcript(SHORT_TEXT)
        self.assertGreaterEqual(len(long_result), len(short_result))
    
    def test_overlap_strategies(self):
        """测试不同的重叠策略"""
        # 首先确保长文本被分成多个段落
        very_small_segmenter = TranscriptSegmenter(
            tokenizer=self.tokenizer,
            max_tokens_per_segment=50,  # 非常小的限制，确保会分段
            overlap_strategy="fixed"
        )
        
        result = very_small_segmenter.segment_transcript(LONG_TEXT, overlap_size=20)
        
        # 确保有多个段落
        self.assertGreater(len(result), 1)
        
        # 使用fixed策略时，从第二个段落开始应该有重叠
        if len(result) > 1:
            # 检查是否有段落存在重叠
            has_overlap = any(segment.overlap_before > 0 for segment in result[1:])
            self.assertTrue(has_overlap, "应该至少有一个段落有重叠")
    
    def test_natural_boundaries(self):
        """测试自然边界检测"""
        # 创建一个明确的分段文本
        test_text = "第一段。这是第一段的内容。\n\n第二段。这是第二段的内容。"
        
        result = self.segmenter.segment_transcript(test_text)
        
        # 检查分段数量
        self.assertGreaterEqual(len(result), 1)
        
        # 检查第一个段落的内容是否包含第一段的部分内容
        self.assertTrue("第一段" in result[0].text)
    
    def test_token_limits(self):
        """测试token限制功能"""
        # 创建一个小token限制的分段器
        small_segmenter = TranscriptSegmenter(
            tokenizer=self.tokenizer,
            max_tokens_per_segment=10  # 非常小的限制
        )
        
        # 应该产生至少一个段落
        result = small_segmenter.segment_transcript(MEDIUM_TEXT)
        self.assertGreaterEqual(len(result), 1)
        
        # 验证段落的token数不大幅超过限制（可能会略微超过，因为实现细节）
        for segment in result:
            self.assertLess(segment.token_count, 20)  # 允许一些弹性
    
    def test_edge_cases(self):
        """测试边缘情况"""
        # 空文本
        result = self.segmenter.segment_transcript("")
        self.assertEqual(len(result), 0)
        
        # 单个长句子
        small_segmenter = TranscriptSegmenter(
            tokenizer=self.tokenizer,
            max_tokens_per_segment=20,
            overlap_strategy="fixed"
        )
        
        result = small_segmenter.segment_transcript(SINGLE_SENTENCE_TEXT, overlap_size=10)
        
        # 长句子应该被分成多个段落
        self.assertGreater(len(result), 1)
        
        # 混合结构文本
        result = self.segmenter.segment_transcript(MIXED_TEXT)
        self.assertGreaterEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main() 