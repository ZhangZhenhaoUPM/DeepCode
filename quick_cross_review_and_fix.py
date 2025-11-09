#!/usr/bin/env python3
"""
Quick Cross Review and Fix

快速交叉审阅和修复工作流
- 只审阅核心文件（避免超时）
- Gemini + Codex 双AI交叉验证
- 自动修复共识问题
- 迭代改进直到达标
"""

import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime


def print_banner(text: str):
    """打印横幅"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def get_core_files(code_directory: Path) -> list:
    """获取核心文件列表（避免审阅太多文件导致超时）"""
    # 优先审阅这些核心文件
    priority_files = [
        "main.py", "model.py", "trainer.py", "data_loader.py",
        "config.py", "utils.py", "train.py", "test.py"
    ]

    core_files = []
    for filename in priority_files:
        file_path = code_directory / filename
        if file_path.exists():
            core_files.append(filename)

    if not core_files:
        # 如果没有找到优先文件，获取所有顶层Python文件
        core_files = [f.name for f in code_directory.glob("*.py")][:5]

    return core_files


def run_gemini_review(code_directory: Path, core_files: list) -> dict:
    """运行Gemini审阅"""
    print_banner("📊 Gemini CLI Review")

    files_str = " ".join(core_files)
    prompt = f"""Review these Python files: {files_str}

For EACH file, provide:
1. Code quality score (0-10)
2. List of issues with severity (CRITICAL/HIGH/MEDIUM/LOW) and exact line numbers
3. Specific recommendations

Then provide overall assessment with top 5 most critical issues to fix.

Output VALID JSON only:
{{
  "files": [
    {{
      "path": "filename.py",
      "score": 7.0,
      "issues": [
        {{"severity": "HIGH", "line": 10, "description": "...", "recommendation": "..."}}
      ]
    }}
  ],
  "overall_score": 7.0,
  "top_issues": [
    {{"file": "file.py", "line": 10, "severity": "HIGH", "issue": "...", "fix": "..."}}
  ]
}}"""

    try:
        result = subprocess.run(
            ["gemini", "-p", prompt],
            cwd=str(code_directory),
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode == 0:
            output = result.stdout

            # 提取JSON
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            else:
                # 找最后一个完整的JSON对象
                json_start = output.find("{")
                json_end = output.rfind("}") + 1
                json_str = output[json_start:json_end]

            data = json.loads(json_str)
            print(f"✅ Gemini Score: {data.get('overall_score', 0)}/10")
            print(f"📋 Found {len(data.get('top_issues', []))} top issues")
            return {"status": "success", "data": data}

    except Exception as e:
        print(f"❌ Gemini error: {e}")

    return {"status": "failed"}


def run_codex_review(code_directory: Path, core_files: list) -> dict:
    """运行Codex审阅"""
    print_banner("🤖 Codex CLI Review")

    files_str = ", ".join(core_files)
    prompt = f"""Review these Python files: {files_str}

For EACH file, provide:
1. Code quality score (0-10)
2. Issues with severity (CRITICAL/HIGH/MEDIUM/LOW) and EXACT line numbers
3. Specific recommendations

Then provide overall assessment with top 5 most critical issues.

Output VALID JSON only:
{{
  "files": [
    {{
      "path": "filename.py",
      "score": 7.0,
      "issues": [
        {{"severity": "HIGH", "line": 10, "description": "...", "recommendation": "..."}}
      ]
    }}
  ],
  "overall_score": 7.0,
  "top_issues": [
    {{"file": "file.py", "line": 10, "severity": "HIGH", "issue": "...", "fix": "..."}}
  ]
}}"""

    try:
        result = subprocess.run(
            ["codex", "exec", prompt],
            cwd=str(code_directory),
            capture_output=True,
            text=True,
            timeout=90
        )

        output = result.stdout + result.stderr

        if "upgrade to Plus" in output:
            print("⚠️  Codex requires Plus subscription")
            return {"status": "skipped"}

        # 提取JSON（Codex输出在最后）
        if "```json" in output:
            json_start = output.find("```json") + 7
            json_end = output.find("```", json_start)
            json_str = output[json_start:json_end].strip()
        else:
            # 找最后一个完整的JSON
            json_start = output.rfind("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
            else:
                raise ValueError("No JSON found in output")

        data = json.loads(json_str)
        print(f"✅ Codex Score: {data.get('overall_score', 0)}/10")
        print(f"📋 Found {len(data.get('top_issues', []))} top issues")
        return {"status": "success", "data": data}

    except Exception as e:
        print(f"❌ Codex error: {e}")

    return {"status": "failed"}


def find_consensus_issues(gemini_data: dict, codex_data: dict) -> list:
    """查找共识问题"""
    print_banner("🔍 Finding Consensus Issues")

    gemini_issues = gemini_data.get("top_issues", [])
    codex_issues = codex_data.get("top_issues", [])

    print(f"Gemini: {len(gemini_issues)} issues")
    print(f"Codex:  {len(codex_issues)} issues")

    consensus = []

    # 按文件和行号匹配
    for g_issue in gemini_issues:
        g_file = g_issue.get("file", "")
        g_line = g_issue.get("line", 0)
        g_severity = g_issue.get("severity", "")

        for c_issue in codex_issues:
            c_file = c_issue.get("file", "")
            c_line = c_issue.get("line", 0)

            # 检查是否是同一个问题（同文件，行号接近）
            if g_file == c_file and abs(g_line - c_line) <= 5:
                consensus.append({
                    "file": g_file,
                    "line": g_line,
                    "severity": g_severity,
                    "gemini_issue": g_issue,
                    "codex_issue": c_issue
                })
                break

    print(f"\n✅ Found {len(consensus)} consensus issues")
    return consensus


def apply_fix(code_directory: Path, issue: dict, iteration: int) -> bool:
    """应用单个修复"""
    file_path = code_directory / issue["file"]
    if not file_path.exists():
        print(f"   ⚠️  File not found: {issue['file']}")
        return False

    print(f"\n   🔧 Fixing: {issue['file']}:{issue['line']}")
    print(f"      Severity: {issue['severity']}")

    # 构建修复提示
    fix_prompt = f"""Fix this issue in {issue['file']} around line {issue['line']}:

Gemini found: {json.dumps(issue['gemini_issue'], indent=2)}
Codex found: {json.dumps(issue['codex_issue'], indent=2)}

Please:
1. Read the file {issue['file']}
2. Locate line {issue['line']} and surrounding code
3. Apply the necessary fix following both recommendations
4. Make the change directly to the file
5. Confirm the fix was applied

Make minimal changes - only fix this specific issue."""

    try:
        result = subprocess.run(
            ["codex", "exec", "--sandbox", "workspace-write", fix_prompt],
            cwd=str(code_directory),
            capture_output=True,
            text=True,
            timeout=60
        )

        if "upgrade to Plus" in result.stdout + result.stderr:
            print(f"   ⚠️  Codex requires Plus")
            return False

        # 检查是否成功
        output = result.stdout + result.stderr
        if "file update:" in output.lower() or "diff" in output.lower():
            print(f"   ✅ Fix applied")
            return True
        elif "applied" in output.lower() or "fixed" in output.lower():
            print(f"   ✅ Fix applied")
            return True
        else:
            print(f"   ⚠️  Fix may not have been applied")
            # 打印输出帮助调试
            print(f"   Output preview: {output[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Timeout while applying fix")
        return False
    except Exception as e:
        print(f"   ❌ Error applying fix: {e}")
        return False


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quick_cross_review_and_fix.py <code_directory> [target_score] [max_iterations]")
        print("\nExample:")
        print("  python quick_cross_review_and_fix.py deepcode_lab/papers/1/generate_code 8.0 3")
        sys.exit(1)

    code_directory = Path(sys.argv[1])
    target_score = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    if not code_directory.exists():
        print(f"❌ Directory not found: {code_directory}")
        sys.exit(1)

    print_banner("🚀 Quick Cross Review and Fix")
    print(f"📁 Directory: {code_directory}")
    print(f"🎯 Target: {target_score}/10")
    print(f"🔄 Max Iterations: {max_iterations}")

    # 检查工具
    has_gemini = shutil.which("gemini") is not None
    has_codex = shutil.which("codex") is not None

    print(f"\n✅ Gemini CLI: {'Available' if has_gemini else 'Not Found'}")
    print(f"✅ Codex CLI:  {'Available' if has_codex else 'Not Found'}")

    if not has_gemini or not has_codex:
        print("\n⚠️  Warning: Both tools recommended for best results")

    # 获取核心文件
    core_files = get_core_files(code_directory)
    print(f"\n📝 Reviewing {len(core_files)} core files: {', '.join(core_files)}")

    # 迭代改进
    for iteration in range(1, max_iterations + 1):
        print_banner(f"🔄 Iteration {iteration}/{max_iterations}")

        # 运行审阅
        gemini_result = run_gemini_review(code_directory, core_files) if has_gemini else {"status": "skipped"}
        codex_result = run_codex_review(code_directory, core_files) if has_codex else {"status": "skipped"}

        # 计算平均分数
        scores = []
        if gemini_result["status"] == "success":
            scores.append(gemini_result["data"].get("overall_score", 0))
        if codex_result["status"] == "success":
            scores.append(codex_result["data"].get("overall_score", 0))

        if not scores:
            print("\n❌ No successful reviews")
            break

        avg_score = sum(scores) / len(scores)
        print_banner(f"📊 Iteration {iteration} Results")
        print(f"Average Score: {avg_score:.2f}/10")

        # 检查是否达标
        if avg_score >= target_score:
            print(f"\n🎯 Target score reached!")
            break

        # 查找共识问题
        if gemini_result["status"] == "success" and codex_result["status"] == "success":
            consensus_issues = find_consensus_issues(
                gemini_result["data"],
                codex_result["data"]
            )

            if not consensus_issues:
                print("\n⚠️  No consensus issues found to fix")
                continue

            # 应用修复
            print_banner(f"🔧 Applying Fixes - Iteration {iteration}")
            fixed_count = 0

            for i, issue in enumerate(consensus_issues, 1):
                print(f"\n[{i}/{len(consensus_issues)}]")
                if apply_fix(code_directory, issue, iteration):
                    fixed_count += 1

            print(f"\n✅ Applied {fixed_count}/{len(consensus_issues)} fixes")

        if iteration < max_iterations:
            print(f"\n⏳ Waiting 3 seconds before next iteration...")
            import time
            time.sleep(3)

    print_banner("🎉 Review and Fix Complete")


if __name__ == "__main__":
    main()
