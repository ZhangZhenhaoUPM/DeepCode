#!/usr/bin/env python3
"""
交叉审阅脚本 - Cross Review with Gemini CLI + Codex CLI

使用两个AI CLI工具进行代码交叉审阅：
1. Google Gemini CLI (免费，60请求/分钟，1000请求/天)
2. OpenAI Codex CLI (需要ChatGPT Plus或API密钥)

Usage:
    python cross_review.py <directory>
    python cross_review.py deepcode_lab/papers/9/generate_code

Features:
    ✅ Gemini CLI自动审阅（推荐）
    ✅ Codex CLI审阅（可选）
    ✅ 支持API fallback
    ✅ 交叉验证结果
    ✅ 生成对比报告
"""

import asyncio
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     🔄 DeepCode - AI Cross Review                             ║
║                                                               ║
║     Google Gemini CLI + OpenAI Codex CLI                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_gemini_cli_installed() -> bool:
    """检查Gemini CLI是否已安装"""
    return shutil.which("gemini") is not None


def check_codex_installed() -> bool:
    """检查Codex CLI是否已安装"""
    return shutil.which("codex") is not None


async def run_gemini_review(directory_path: str) -> tuple[bool, str]:
    """运行Gemini API审阅"""
    try:
        from workflows.code_review_workflow_gemini import CodeReviewWorkflowGemini

        print("\n" + "="*70)
        print("📊 STEP 1: Gemini 2.5 Pro Automated Review")
        print("="*70)
        print("\n🤖 Starting Gemini 2.5 Pro review...")

        workflow = CodeReviewWorkflowGemini()
        results = await workflow.review_directory(directory_path)

        if results["status"] == "success":
            # Save report
            output_path = Path(directory_path).parent / "code_reviews" / "gemini_review.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            await workflow.generate_review_report(results, str(output_path))

            summary = results["summary"]
            print(f"\n   ✅ Gemini review completed!")
            print(f"   📊 Score: {summary['average_score']}/10")
            print(f"   📋 Issues: {summary['total_issues']}")
            print(f"      - Critical: {summary['critical_issues']}")
            print(f"      - High: {summary['high_issues']}")
            print(f"      - Medium: {summary['medium_issues']}")
            print(f"      - Low: {summary['low_issues']}")
            print(f"   💾 Report: {output_path}")

            return True, str(output_path)
        else:
            print(f"\n   ⚠️  Gemini review failed: {results.get('error')}")
            return False, None

    except ValueError as e:
        print(f"\n   ℹ️  Gemini not configured: {e}")
        print("\n   📝 To configure Gemini API:")
        print("      1. Get API key: https://aistudio.google.com/apikey")
        print("      2. Edit mcp_agent.secrets.yaml:")
        print("         openai:")
        print('           api_key: "YOUR_GEMINI_API_KEY"')
        print('           base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"')
        return False, None
    except Exception as e:
        print(f"\n   ⚠️  Gemini review error: {e}")
        return False, None


def run_gemini_cli_review(directory_path: str) -> tuple[bool, str]:
    """运行Gemini CLI审阅"""
    print("\n" + "="*70)
    print("📊 STEP 1: Google Gemini CLI Review")
    print("="*70)

    if not check_gemini_cli_installed():
        print("\n   ℹ️  Gemini CLI not installed")
        print("\n   📝 To install Gemini CLI:")
        print("      npm install -g @google/gemini-cli")
        print("      # or")
        print("      brew install gemini-cli")
        print("\n   📖 Docs: https://github.com/google-gemini/gemini-cli")
        print("\n   💡 Fallback: Trying Gemini API...")
        return run_gemini_api_fallback(directory_path)

    print("\n🤖 Gemini CLI detected!")

    directory = Path(directory_path)
    review_dir = directory.parent / "code_reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    output_file = review_dir / "gemini_cli_review.md"

    # Create review prompt
    prompt = f"""Review all Python files in the current directory for:
1. Code quality and maintainability
2. Security vulnerabilities
3. Performance issues
4. Best practices compliance
5. Bug detection

For each file, provide:
- Overall score (0-10)
- Specific issues with severity (CRITICAL/HIGH/MEDIUM/LOW)
- Line numbers where applicable
- Concrete recommendations

Format the output as a detailed Markdown report."""

    print(f"\n   🚀 Running Gemini CLI review...")
    print(f"   📂 Directory: {directory}")

    try:
        # Run gemini CLI with the prompt
        result = subprocess.run(
            ["gemini", "-p", prompt, "--include-directories", str(directory)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        if result.returncode == 0:
            # Save output
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# Gemini CLI Code Review\n\n")
                f.write(f"**Generated**: {datetime.now().isoformat()}\n")
                f.write(f"**Directory**: {directory_path}\n")
                f.write(f"**Model**: Gemini 2.5 Pro (via CLI)\n\n")
                f.write("---\n\n")
                f.write(result.stdout)

            print(f"\n   ✅ Gemini CLI review completed!")
            print(f"   💾 Report: {output_file}")
            return True, str(output_file)
        else:
            print(f"\n   ⚠️  Gemini CLI error: {result.stderr}")
            print("\n   💡 Fallback: Trying Gemini API...")
            return run_gemini_api_fallback(directory_path)

    except subprocess.TimeoutExpired:
        print(f"\n   ⚠️  Gemini CLI timeout (5min)")
        print("\n   💡 Fallback: Trying Gemini API...")
        return run_gemini_api_fallback(directory_path)
    except Exception as e:
        print(f"\n   ⚠️  Gemini CLI error: {e}")
        print("\n   💡 Fallback: Trying Gemini API...")
        return run_gemini_api_fallback(directory_path)


def run_gemini_api_fallback(directory_path: str) -> tuple[bool, str]:
    """Gemini API fallback when CLI not available"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(run_gemini_review(directory_path))
    except:
        return False, None


def run_codex_review(directory_path: str) -> tuple[bool, str]:
    """运行Codex CLI审阅"""
    print("\n" + "="*70)
    print("📊 STEP 2: OpenAI Codex CLI Review")
    print("="*70)

    if not check_codex_installed():
        print("\n   ℹ️  Codex CLI not installed")
        print("\n   📝 To install Codex CLI:")
        print("      npm install -g @openai/codex")
        print("      # or")
        print("      brew install codex")
        print("\n   📖 Docs: https://developers.openai.com/codex/cli/")
        return False, None

    print("\n🤖 Codex CLI detected!")

    directory = Path(directory_path)
    review_dir = directory.parent / "code_reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    codex_output = review_dir / "codex_review.md"

    # Create a review prompt file for Codex
    prompt_file = review_dir / "codex_review_prompt.txt"

    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(f"""Review all Python files in this directory: {directory}

Please perform a comprehensive security and code quality review:

1. Look for security vulnerabilities
2. Check code quality and best practices
3. Identify potential bugs or logic errors
4. Assess performance issues
5. Review error handling
6. Check documentation quality

For each file, provide:
- Overall score (0-10)
- List of issues with severity (CRITICAL/HIGH/MEDIUM/LOW)
- Specific recommendations

Save your detailed review analysis to: {codex_output}
""")

    print(f"\n   📝 Created review prompt: {prompt_file}")
    print(f"\n   🚀 Launching Codex CLI...")
    print(f"\n   ℹ️  You need to:")
    print(f"      1. Navigate to: cd {directory}")
    print(f"      2. Run: codex")
    print(f"      3. In Codex, paste this prompt:")
    print(f"\n" + "-"*70)

    with open(prompt_file, "r") as f:
        print(f.read())

    print("-"*70)
    print(f"\n   4. Let Codex analyze the code")
    print(f"   5. Save Codex's response to: {codex_output}")
    print(f"\n   💡 Or use the /review command in Codex for automated review")

    # Try to open terminal with codex (platform-specific)
    try:
        import platform
        system = platform.system()

        if system == "Darwin":  # macOS
            print(f"\n   🎯 Opening Terminal with Codex...")
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "cd {directory} && codex"'
            ])
        elif system == "Linux":
            print(f"\n   🎯 Attempting to open terminal...")
            # Try different terminal emulators
            for terminal in ["gnome-terminal", "konsole", "xterm"]:
                if shutil.which(terminal):
                    subprocess.Popen([
                        terminal, "--", "bash", "-c",
                        f"cd {directory} && codex; exec bash"
                    ])
                    break
    except Exception as e:
        print(f"\n   ℹ️  Could not auto-open terminal: {e}")
        print(f"   Please manually run: cd {directory} && codex")

    # Check if review was completed
    print(f"\n   ⏳ Waiting for Codex review to complete...")
    print(f"   📄 Checking for: {codex_output}")
    print(f"\n   Press Enter when Codex review is saved to the file...")

    input()

    if codex_output.exists():
        print(f"\n   ✅ Codex review found: {codex_output}")
        return True, str(codex_output)
    else:
        print(f"\n   ⚠️  Codex review file not found")
        print(f"   Please save Codex's review manually to: {codex_output}")
        return False, None


def generate_cross_review_summary(
    directory_path: str,
    gemini_report: str,
    codex_report: str
) -> str:
    """生成交叉审阅汇总"""
    directory = Path(directory_path)
    review_dir = directory.parent / "code_reviews"
    summary_file = review_dir / "CROSS_REVIEW_SUMMARY.md"

    lines = [
        "# Cross-Review Summary Report",
        f"\n**Generated**: {datetime.now().isoformat()}",
        f"**Directory**: {directory_path}",
        f"**Models**: Gemini 2.5 Pro + OpenAI Codex CLI\n",
        "## Review Status\n"
    ]

    if gemini_report:
        lines.append(f"- ✅ **Gemini 2.5 Pro**: [View Report](./{Path(gemini_report).name})")
    else:
        lines.append(f"- ⏸️  **Gemini 2.5 Pro**: Not completed")

    if codex_report:
        lines.append(f"- ✅ **Codex CLI**: [View Report](./{Path(codex_report).name})")
    else:
        lines.append(f"- ⏸️  **Codex CLI**: Not completed")

    lines.extend([
        "\n## How to Compare Results\n",
        "1. **Review both reports**:",
        f"   - Gemini: `{gemini_report if gemini_report else 'N/A'}`",
        f"   - Codex: `{codex_report if codex_report else 'N/A'}`\n",
        "2. **Identify common issues**:",
        "   - Issues found by both models → High priority",
        "   - Model-specific findings → Verify manually\n",
        "3. **Create action plan**:",
        "   - Prioritize issues by severity and consensus",
        "   - Address critical issues first",
        "   - Consider unique insights from each model\n",
        "## Consensus Issues\n",
        "<!-- After reviewing both reports, list issues identified by both models -->\n",
        "TBD - Compare reports manually\n",
        "## Action Items\n",
        "- [ ] Review Gemini findings",
        "- [ ] Review Codex findings",
        "- [ ] Identify consensus issues",
        "- [ ] Prioritize fixes",
        "- [ ] Implement improvements",
        "- [ ] Re-run reviews to validate fixes\n"
    ])

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(summary_file)


async def main():
    """主函数"""
    print_banner()

    # Check arguments
    if len(sys.argv) < 2:
        print("\nUsage: python cross_review.py <directory_path>\n")
        print("Example:")
        print("  python cross_review.py deepcode_lab/papers/9/generate_code\n")

        # Show recent directories
        deepcode_lab = Path("deepcode_lab/papers")
        if deepcode_lab.exists():
            generate_code_dirs = sorted(
                deepcode_lab.glob("*/generate_code"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if generate_code_dirs:
                print("📁 Recently modified directories:")
                for i, gdir in enumerate(generate_code_dirs[:5], 1):
                    py_count = len(list(gdir.rglob("*.py")))
                    if py_count > 0:
                        print(f"   {i}. {gdir} ({py_count} files)")
        print()
        sys.exit(1)

    directory_path = sys.argv[1]
    directory = Path(directory_path)

    if not directory.exists():
        print(f"\n❌ Error: Directory not found: {directory_path}\n")
        sys.exit(1)

    # Count Python files
    py_files = list(directory.rglob("*.py"))
    if not py_files:
        print(f"\n❌ Error: No Python files found in {directory_path}\n")
        sys.exit(1)

    print(f"\n📁 Target directory: {directory_path}")
    print(f"🐍 Found {len(py_files)} Python file(s)\n")

    # Run Gemini CLI review (with API fallback)
    gemini_success, gemini_report = run_gemini_cli_review(directory_path)

    # Run Codex review
    codex_success, codex_report = run_codex_review(directory_path)

    # Generate summary
    print("\n" + "="*70)
    print("📋 STEP 3: Generating Cross-Review Summary")
    print("="*70)

    summary_file = generate_cross_review_summary(
        directory_path,
        gemini_report if gemini_success else None,
        codex_report if codex_success else None
    )

    print(f"\n   ✅ Summary created: {summary_file}")

    # Final report
    print("\n" + "="*70)
    print("✅ CROSS-REVIEW COMPLETE")
    print("="*70)

    print(f"\n📊 Review Status:")
    if gemini_success:
        print(f"   ✅ Gemini 2.5 Pro: COMPLETED")
        print(f"      Report: {gemini_report}")
    else:
        print(f"   ⏸️  Gemini 2.5 Pro: SKIPPED or FAILED")

    if codex_success:
        print(f"   ✅ Codex CLI: COMPLETED")
        print(f"      Report: {codex_report}")
    else:
        print(f"   ⏸️  Codex CLI: SKIPPED or PENDING")

    print(f"\n📄 Cross-Review Summary: {summary_file}")

    if gemini_success and codex_success:
        print("\n🎉 Both reviews completed! Compare results in the summary.")
    elif gemini_success or codex_success:
        print("\n⚠️  Partial review completed. Configure missing tool for full cross-review.")
    else:
        print("\n❌ No reviews completed. Please configure at least one tool.")

    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
