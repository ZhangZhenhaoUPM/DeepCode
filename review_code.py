#!/usr/bin/env python3
"""
便捷的代码审阅脚本 - Convenient Code Review Script

使用Gemini 2.5 Pro对生成的代码进行专业审阅
Uses Gemini 2.5 Pro to professionally review generated code

Usage:
    python review_code.py <directory>
    python review_code.py deepcode_lab/papers/9/generate_code

Features:
    ✅ 自动检测Python文件
    ✅ 全面的代码质量评估
    ✅ 安全性和性能分析
    ✅ 生成详细的Markdown报告
    ✅ 问题分类和优先级排序
"""

import asyncio
import sys
from pathlib import Path
from workflows.code_review_workflow_gemini import CodeReviewWorkflowGemini


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        🤖 DeepCode - AI Code Review with Gemini 2.5 Pro      ║
║                                                               ║
║  Professional code review powered by Google's latest AI      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def review_generated_code(directory_path: str):
    """审阅生成的代码"""

    # Check if directory exists
    directory = Path(directory_path)
    if not directory.exists():
        print(f"❌ Error: Directory not found: {directory_path}")
        print(f"\nPlease provide a valid directory path containing generated code.")
        return False

    # Check for Python files
    py_files = list(directory.rglob("*.py"))
    if not py_files:
        print(f"❌ Error: No Python files found in {directory_path}")
        return False

    print(f"\n📁 Directory: {directory_path}")
    print(f"🐍 Found {len(py_files)} Python file(s) to review\n")

    # Initialize workflow
    try:
        workflow = CodeReviewWorkflowGemini()
        print(f"✅ Initialized Gemini 2.5 Pro reviewer\n")
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("📝 To configure Gemini API:")
        print("   1. Get API key from: https://aistudio.google.com/apikey")
        print("   2. Edit mcp_agent.secrets.yaml:")
        print("      openai:")
        print('        api_key: "YOUR_GEMINI_API_KEY_HERE"')
        print('        base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"\n')
        return False
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

    # Start review
    print("🔍 Starting comprehensive code review...")
    print("   This may take a few minutes depending on code size.\n")

    try:
        results = await workflow.review_directory(
            directory_path,
            file_pattern="*.py",
            exclude_patterns=["**/test_*.py", "**/__pycache__/**", "**/.*", "**/.venv/**"]
        )

        if results["status"] != "success":
            print(f"❌ Review failed: {results.get('error', 'Unknown error')}")
            return False

        # Generate report
        output_path = directory.parent / "code_review_report.md"
        report = await workflow.generate_review_report(results, str(output_path))

        # Print summary
        summary = results["summary"]

        print("\n" + "="*70)
        print("📊 REVIEW SUMMARY")
        print("="*70)
        print(f"\n✅ Successfully reviewed: {summary['reviewed_successfully']}/{summary['total_files']} files")

        # Score with color coding
        avg_score = summary['average_score']
        if avg_score >= 8.0:
            score_emoji = "🌟"
        elif avg_score >= 6.0:
            score_emoji = "✅"
        elif avg_score >= 4.0:
            score_emoji = "⚠️"
        else:
            score_emoji = "❌"

        print(f"{score_emoji} Average Quality Score: {avg_score}/10")

        # Issues summary
        total_issues = summary['total_issues']
        critical = summary['critical_issues']
        high = summary['high_issues']
        medium = summary['medium_issues']
        low = summary['low_issues']

        print(f"\n📋 Issues Found: {total_issues} total")
        if critical > 0:
            print(f"   🔴 Critical: {critical}")
        if high > 0:
            print(f"   🟠 High:     {high}")
        if medium > 0:
            print(f"   🟡 Medium:   {medium}")
        if low > 0:
            print(f"   🟢 Low:      {low}")

        print(f"\n📄 Detailed report saved to:")
        print(f"   {output_path}")
        print("\n" + "="*70)

        # Recommendations
        if critical > 0:
            print("\n⚠️  ATTENTION: Critical issues found! Please review immediately.")
        elif high > 0:
            print("\n⚠️  High priority issues detected. Recommended to address soon.")
        elif avg_score >= 8.0:
            print("\n🎉 Excellent code quality! Keep up the good work!")

        return True

    except Exception as e:
        print(f"\n❌ Review error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print_banner()

    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python review_code.py <directory_path>\n")
        print("Examples:")
        print("  python review_code.py deepcode_lab/papers/9/generate_code")
        print("  python review_code.py deepcode_lab/papers/1/generate_code\n")

        # Try to find the most recent generate_code directory
        deepcode_lab = Path("deepcode_lab/papers")
        if deepcode_lab.exists():
            generate_code_dirs = sorted(
                deepcode_lab.glob("*/generate_code"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if generate_code_dirs:
                print("📁 Recently modified generate_code directories:")
                for i, gdir in enumerate(generate_code_dirs[:5], 1):
                    py_count = len(list(gdir.rglob("*.py")))
                    if py_count > 0:
                        print(f"   {i}. {gdir} ({py_count} Python files)")

        sys.exit(1)

    directory_path = sys.argv[1]

    # Run review
    success = await review_generated_code(directory_path)

    if success:
        print("\n✅ Code review completed successfully!\n")
        sys.exit(0)
    else:
        print("\n❌ Code review failed.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
