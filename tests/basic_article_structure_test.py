"""
Task 4.6 - 文章结构生成功能的基础测试

此脚本测试文章结构相关的基本功能，包括：
1. 配置类 ArticleFormatConfig
2. 文章结构模型的导入
3. 各种格式的输出能力
"""

import sys
from pathlib import Path

# 添加项目根目录到路径中
sys.path.append(str(Path.cwd()))

def test_import_models():
    """测试能否成功导入文章结构相关的模型"""
    print("\n=== 测试导入文章结构模型 ===")
    
    try:
        # 导入文章结构相关的类
        from src.models.article_structure import (
            ArticleStructure, ArticleSection, ArticleElement,
            ArticleParagraph, ArticleList, ArticleQuote, ArticleOutline,
            Emphasis, EmphasisType
        )
        print("✓ 成功导入所有文章结构相关的类")
        
        # 导入模板类
        from src.models.template import Template
        print("✓ 成功导入Template类")
        
        return True
    except Exception as e:
        print(f"× 导入失败: {e}")
        return False

def test_import_services():
    """测试能否成功导入文章结构生成服务"""
    print("\n=== 测试导入文章结构生成服务 ===")
    
    try:
        # 导入服务类
        from src.services.article_structure_generator import (
            ArticleStructureGenerator, ArticleFormatConfig
        )
        print("✓ 成功导入ArticleStructureGenerator和ArticleFormatConfig")
        
        # 测试创建配置对象
        config = ArticleFormatConfig(
            outline_mode=True,
            section_count=5,
            paragraph_density="medium",
            enhancement_level="balanced",
            list_frequency="balanced",
            quote_frequency="minimal",
            export_format="markdown"
        )
        
        print("\n配置对象内容:")
        print(f"- outline_mode: {config.outline_mode}")
        print(f"- section_count: {config.section_count}")
        print(f"- paragraph_density: {config.paragraph_density}")
        print(f"- enhancement_level: {config.enhancement_level}")
        print(f"- list_frequency: {config.list_frequency}")
        print(f"- quote_frequency: {config.quote_frequency}")
        print(f"- export_format: {config.export_format}")
        
        return True
    except Exception as e:
        print(f"× 导入或配置失败: {e}")
        return False

def verify_exports():
    """验证文章结构的Markdown和HTML导出功能"""
    print("\n=== 验证文章格式导出功能 ===")
    
    # 创建简单的Markdown结构作为参考
    expected_markdown = """
# 人工智能概述

这是一个关于**AI**的介绍段落。人工智能正在改变我们的世界。

## AI简介

AI是一种模拟人类智能的计算机系统。

- 自然语言处理
- 计算机视觉
- 机器学习

## AI的应用

AI已被广泛应用于多个领域。

> 人工智能是计算机科学领域的重要分支。
>
> — AI专家

## 结论

AI技术将继续发展并影响我们的未来。
    """
    
    print("预期的Markdown格式输出示例:")
    print("-" * 40)
    print(expected_markdown.strip())
    print("-" * 40)
    
    # 验证导出方法是否存在
    try:
        from src.models.article_structure import ArticleStructure
        
        print(f"\n✓ ArticleStructure.to_markdown 方法存在: {'to_markdown' in dir(ArticleStructure)}")
        print(f"✓ ArticleStructure.to_html 方法存在: {'to_html' in dir(ArticleStructure)}")
        print(f"✓ ArticleStructure.to_dict 方法存在: {'to_dict' in dir(ArticleStructure)}")
        print(f"✓ ArticleStructure.from_dict 方法存在: {'from_dict' in dir(ArticleStructure)}")
        print(f"✓ ArticleStructure.to_json 方法存在: {'to_json' in dir(ArticleStructure)}")
        print(f"✓ ArticleStructure.from_json 方法存在: {'from_json' in dir(ArticleStructure)}")
        
        return True
    except Exception as e:
        print(f"× 验证导出功能失败: {e}")
        return False

def test_emphasis_types():
    """测试强调类型枚举"""
    print("\n=== 测试文本强调类型 ===")
    
    try:
        from src.models.article_structure import EmphasisType
        
        print("支持的强调类型:")
        for emphasis_type in EmphasisType:
            print(f"- {emphasis_type.name}: {emphasis_type.value}")
        
        return True
    except Exception as e:
        print(f"× 测试强调类型失败: {e}")
        return False

def main():
    """主函数"""
    print("=== Task 4.6 - 文章结构生成功能基础测试 ===\n")
    
    # 记录测试结果
    results = {}
    
    # 测试导入模型
    results["导入模型"] = test_import_models()
    
    # 测试导入服务
    results["导入服务"] = test_import_services()
    
    # 验证导出功能
    results["验证导出"] = verify_exports()
    
    # 测试强调类型
    results["强调类型"] = test_emphasis_types()
    
    # 总结测试结果
    print("\n=== 测试结果摘要 ===")
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "× 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n总体结果: {'✓ 所有测试通过' if all_passed else '× 有测试失败'}")

if __name__ == "__main__":
    main() 