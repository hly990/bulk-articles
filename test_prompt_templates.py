#!/usr/bin/env python
"""
测试脚本 - Medium风格提示模板 (Task 4.3)

此脚本测试src/services/prompt_templates.py中的功能，
包括不同语气的模板、PromptAssembler和各种扩展功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.services.prompt_templates import (
    PromptAssembler, 
    MEDIUM_TEMPLATES, 
    TONE_SPECIFIC_GUIDANCE,
    DEFAULT_SECTIONS,
    OPTIONAL_SECTIONS
)
from src.models.template import Template
from src.app.constants import (
    TONE_PROFESSIONAL, TONE_CASUAL, TONE_STORYTELLING,
    TONE_TECHNICAL, TONE_EDUCATIONAL
)

def print_separator(title):
    """打印分隔符和标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_basic_template_generation():
    """测试基础模板生成"""
    print_separator("基础模板生成测试")
    
    # 创建基本的模板实例
    template = Template(
        name="测试模板",
        tone=TONE_PROFESSIONAL,
        brand="YT-Article Craft",
        cta="点击订阅获取更多优质内容！"
    )
    
    # 创建默认的PromptAssembler
    assembler = PromptAssembler()
    
    # 生成提示
    transcript = "这是一段测试用的视频转录内容，用于生成文章。"
    prompt = assembler.build_prompt(
        template=template,
        transcript_segment=transcript
    )
    
    print(f"生成的提示长度: {len(prompt)} 字符")
    print(f"模板名称: {template.name}")
    print(f"语气类型: {template.tone}")
    print(f"提示中使用的部分: {[section.name for section in assembler.sections]}")
    
    # 打印前100个字符和最后100个字符的片段
    print("\n提示片段预览:")
    print(f"开头: {prompt[:100]}...")
    print(f"结尾: ...{prompt[-100:]}")

def test_all_tone_templates():
    """测试所有语气类型的模板"""
    print_separator("不同语气类型的模板测试")
    
    # 定义要测试的所有语气类型
    tones = [
        TONE_PROFESSIONAL,
        TONE_CASUAL, 
        TONE_STORYTELLING,
        TONE_TECHNICAL,
        TONE_EDUCATIONAL
    ]
    
    transcript = "这是一段简短的视频转录内容，我们将测试不同语气下的提示生成。"
    
    for tone in tones:
        print(f"\n测试语气: {tone}")
        
        template = Template(
            name=f"{tone.capitalize()} 模板",
            tone=tone,
            brand="YT-Article Craft" if tone != TONE_CASUAL else "非正式博客",
            cta="订阅我们的频道!" if tone != TONE_TECHNICAL else "参考我们的技术文档获取更多信息"
        )
        
        assembler = PromptAssembler()
        prompt = assembler.build_prompt(
            template=template,
            transcript_segment=transcript
        )
        
        # 查找并打印语气特定的指导
        print(f"  该语气的介绍部分指导: {TONE_SPECIFIC_GUIDANCE[tone]['intro']}")
        
        # 打印总长度
        print(f"  生成的提示长度: {len(prompt)} 字符")
        
        # 查找并打印增强的部分 (仅打印一小部分)
        intro_start = prompt.find("### Introduction")
        if intro_start > 0:
            intro_end = prompt.find("###", intro_start + 5)
            intro_preview = prompt[intro_start:intro_start+100] + "..."
            print(f"  介绍部分预览: {intro_preview}")

def test_optional_sections():
    """测试可选部分的添加"""
    print_separator("可选部分测试 (SEO, 引文建议)")
    
    template = Template(
        name="带可选部分的模板",
        tone=TONE_PROFESSIONAL,
        brand="YT-Article Craft",
        cta="了解更多内容!"
    )
    
    # 创建包含可选部分的PromptAssembler
    assembler = PromptAssembler(
        optional_sections=["seo", "pull_quote"]
    )
    
    transcript = "这是测试可选部分的转录内容。"
    prompt = assembler.build_prompt(
        template=template,
        transcript_segment=transcript
    )
    
    print(f"包含可选部分的提示长度: {len(prompt)} 字符")
    print(f"提示中使用的部分: {[section.name for section in assembler.sections]}")
    
    # 查找并打印SEO部分和引文建议部分
    seo_start = prompt.find("### SEO Optimization")
    if seo_start > 0:
        seo_preview = prompt[seo_start:seo_start+100] + "..."
        print(f"\nSEO部分预览: {seo_preview}")
    
    quote_start = prompt.find("### Pull Quote Suggestion")
    if quote_start > 0:
        quote_preview = prompt[quote_start:quote_start+100] + "..."
        print(f"\n引文建议部分预览: {quote_preview}")

def test_extra_instructions():
    """测试添加额外指令"""
    print_separator("额外指令测试")
    
    template = Template(
        name="带额外指令的模板",
        tone=TONE_EDUCATIONAL,
        brand="教育平台",
        cta="参加我们的课程!"
    )
    
    assembler = PromptAssembler()
    transcript = "这是测试额外指令的转录内容。"
    
    extra_instructions = """
    请确保文章适合初学者理解。
    使用更多的例子和类比来解释复杂概念。
    避免使用太多专业术语。
    """
    
    prompt = assembler.build_prompt(
        template=template,
        transcript_segment=transcript,
        extra_instructions=extra_instructions
    )
    
    print(f"带额外指令的提示长度: {len(prompt)} 字符")
    
    # 查找并打印额外指令部分
    extra_start = prompt.find("### Additional Instructions")
    if extra_start > 0:
        extra_preview = prompt[extra_start:extra_start+150] + "..."
        print(f"\n额外指令部分预览: {extra_preview}")

if __name__ == "__main__":
    print("开始测试Medium风格提示模板...\n")
    
    # 运行所有测试
    test_basic_template_generation()
    test_all_tone_templates()
    test_optional_sections()
    test_extra_instructions()
    
    print("\n所有测试完成!") 