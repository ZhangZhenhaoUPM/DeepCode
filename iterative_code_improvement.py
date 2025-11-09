#!/usr/bin/env python3
"""
Iterative Code Improvement Workflow

使用Gemini CLI和Codex CLI进行交叉审阅和迭代改进：
1. 两个AI工具独立审阅代码
2. 汇总审阅结果，计算共识分数
3. 根据共识问题进行代码修改
4. 重新审阅验证改进
5. 重复直到达到目标质量

Features:
- 双AI交叉验证
- 共识问题优先修复
- 迭代改进直到达标
- 完整的审阅和修改历史
"""

import asyncio
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class IterativeCodeImprover:
    """迭代代码改进器"""

    def __init__(
        self,
        code_directory: str,
        target_score: float = 8.0,
        max_iterations: int = 5
    ):
        """
        初始化

        Args:
            code_directory: 代码目录路径
            target_score: 目标质量分数 (0-10)
            max_iterations: 最大迭代次数
        """
        self.code_directory = Path(code_directory)
        self.target_score = target_score
        self.max_iterations = max_iterations

        # 创建输出目录
        self.output_dir = self.code_directory.parent / "iterative_reviews"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 审阅历史
        self.review_history = []

    def print_banner(self, text: str, char: str = "="):
        """打印横幅"""
        print("\n" + char * 70)
        print(f"  {text}")
        print(char * 70 + "\n")

    def check_tools_available(self) -> Dict[str, bool]:
        """检查工具可用性"""
        self.print_banner("🔧 Checking Available Tools")

        tools = {
            "gemini": shutil.which("gemini") is not None,
            "codex": shutil.which("codex") is not None
        }

        print(f"✅ Gemini CLI: {'Available' if tools['gemini'] else 'Not Found'}")
        print(f"✅ Codex CLI:  {'Available' if tools['codex'] else 'Not Found'}")

        if not tools["gemini"] and not tools["codex"]:
            print("\n❌ Error: No review tools available!")
            print("   Install at least one: gemini or codex CLI")
            return tools

        if not tools["gemini"]:
            print("\n⚠️  Warning: Gemini CLI not found, using Codex only")
        if not tools["codex"]:
            print("\n⚠️  Warning: Codex CLI not found, using Gemini only")

        return tools

    def run_gemini_review(self, iteration: int) -> Dict[str, Any]:
        """运行Gemini审阅"""
        print("\n📊 Running Gemini CLI Review...")

        prompt = """Review all Python files in this directory comprehensively.

For each file, provide:
1. Code quality score (0-10)
2. Issues found with severity (CRITICAL/HIGH/MEDIUM/LOW) and line numbers
3. Specific recommendations for improvement

Then provide:
- Overall average score across all files
- Top 5 most critical issues that need fixing
- Summary of code quality

Format as JSON with this structure:
{
  "files": [
    {
      "path": "file.py",
      "score": 7.5,
      "issues": [
        {"severity": "HIGH", "line": 10, "description": "...", "recommendation": "..."}
      ]
    }
  ],
  "overall_score": 7.2,
  "critical_issues": [
    {"file": "file.py", "line": 10, "issue": "...", "severity": "HIGH"}
  ],
  "summary": "..."
}"""

        try:
            result = subprocess.run(
                ["gemini", "-p", prompt, "--include-directories", str(self.code_directory)],
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode == 0:
                # 保存完整输出
                output_file = self.output_dir / f"iteration_{iteration}_gemini_raw.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                # 尝试解析JSON
                try:
                    # 提取JSON部分
                    output = result.stdout
                    if "```json" in output:
                        json_start = output.find("```json") + 7
                        json_end = output.find("```", json_start)
                        json_str = output[json_start:json_end].strip()
                    elif "{" in output:
                        json_start = output.find("{")
                        json_end = output.rfind("}") + 1
                        json_str = output[json_start:json_end]
                    else:
                        json_str = output

                    review_data = json.loads(json_str)
                    print(f"   ✅ Gemini review completed")
                    print(f"   📊 Overall Score: {review_data.get('overall_score', 'N/A')}/10")
                    return {
                        "status": "success",
                        "tool": "gemini",
                        "data": review_data,
                        "raw_output": output
                    }

                except json.JSONDecodeError as e:
                    print(f"   ⚠️  JSON parsing failed: {e}")
                    print(f"   📄 Using raw text analysis")
                    return {
                        "status": "partial",
                        "tool": "gemini",
                        "data": self.parse_text_review(result.stdout),
                        "raw_output": result.stdout
                    }
            else:
                print(f"   ❌ Gemini failed: {result.stderr}")
                return {"status": "failed", "tool": "gemini", "error": result.stderr}

        except subprocess.TimeoutExpired:
            print(f"   ⚠️  Gemini timeout")
            return {"status": "failed", "tool": "gemini", "error": "Timeout"}
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {"status": "failed", "tool": "gemini", "error": str(e)}

    def run_codex_review(self, iteration: int) -> Dict[str, Any]:
        """运行Codex审阅"""
        print("\n🤖 Running Codex CLI Review...")

        prompt = """Review all Python files in this directory comprehensively.

For each file, provide:
1. Code quality score (0-10)
2. Issues found with severity (CRITICAL/HIGH/MEDIUM/LOW) and specific line numbers
3. Concrete recommendations for improvement

Then provide:
- Overall average score across all files
- Top 5 most critical issues that need immediate fixing
- Summary of overall code quality

Format as JSON with this structure:
{
  "files": [
    {
      "path": "file.py",
      "score": 7.5,
      "issues": [
        {"severity": "HIGH", "line": 10, "description": "...", "recommendation": "..."}
      ]
    }
  ],
  "overall_score": 7.2,
  "critical_issues": [
    {"file": "file.py", "line": 10, "issue": "...", "severity": "HIGH"}
  ],
  "summary": "..."
}"""

        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                cwd=str(self.code_directory),
                capture_output=True,
                text=True,
                timeout=180
            )

            output = result.stdout + result.stderr

            # 检查订阅问题
            if "upgrade to Plus" in output:
                print(f"   ⚠️  Codex requires ChatGPT Plus subscription")
                return {"status": "failed", "tool": "codex", "error": "Requires Plus"}

            # 保存完整输出
            output_file = self.output_dir / f"iteration_{iteration}_codex_raw.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)

            # 尝试解析JSON
            try:
                # 提取JSON部分（Codex输出在最后）
                if "```json" in output:
                    json_start = output.find("```json") + 7
                    json_end = output.find("```", json_start)
                    json_str = output[json_start:json_end].strip()
                elif "{" in output:
                    # 找到最后一个完整的JSON对象
                    json_start = output.rfind("{")
                    json_end = output.rfind("}") + 1
                    json_str = output[json_start:json_end]
                else:
                    json_str = output

                review_data = json.loads(json_str)
                print(f"   ✅ Codex review completed")
                print(f"   📊 Overall Score: {review_data.get('overall_score', 'N/A')}/10")
                return {
                    "status": "success",
                    "tool": "codex",
                    "data": review_data,
                    "raw_output": output
                }

            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON parsing failed: {e}")
                print(f"   📄 Using raw text analysis")
                return {
                    "status": "partial",
                    "tool": "codex",
                    "data": self.parse_text_review(output),
                    "raw_output": output
                }

        except subprocess.TimeoutExpired:
            print(f"   ⚠️  Codex timeout")
            return {"status": "failed", "tool": "codex", "error": "Timeout"}
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {"status": "failed", "tool": "codex", "error": str(e)}

    def parse_text_review(self, text: str) -> Dict[str, Any]:
        """从文本中解析审阅结果（fallback）"""
        import re

        # 尝试提取分数
        scores = re.findall(r'score[:\s]+(\d+(?:\.\d+)?)/10', text, re.IGNORECASE)
        avg_score = sum(float(s) for s in scores) / len(scores) if scores else 5.0

        # 尝试提取问题
        issues = []
        severity_pattern = r'(CRITICAL|HIGH|MEDIUM|LOW)[:\s]+(.*?)(?=\n|$)'
        matches = re.findall(severity_pattern, text, re.IGNORECASE)

        for severity, description in matches:
            issues.append({
                "severity": severity.upper(),
                "description": description.strip()
            })

        return {
            "overall_score": avg_score,
            "critical_issues": issues[:5],  # Top 5
            "summary": "Parsed from text output"
        }

    def generate_consensus_report(
        self,
        gemini_result: Dict[str, Any],
        codex_result: Dict[str, Any],
        iteration: int
    ) -> Dict[str, Any]:
        """生成共识报告"""
        self.print_banner(f"📋 Generating Consensus Report - Iteration {iteration}")

        consensus = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "gemini_status": gemini_result["status"],
            "codex_status": codex_result["status"],
            "scores": {},
            "consensus_issues": [],
            "average_score": 0.0
        }

        # 提取分数
        scores = []
        if gemini_result["status"] in ["success", "partial"]:
            gemini_score = gemini_result["data"].get("overall_score", 0)
            consensus["scores"]["gemini"] = gemini_score
            scores.append(gemini_score)
            print(f"   Gemini Score: {gemini_score}/10")

        if codex_result["status"] in ["success", "partial"]:
            codex_score = codex_result["data"].get("overall_score", 0)
            consensus["scores"]["codex"] = codex_score
            scores.append(codex_score)
            print(f"   Codex Score:  {codex_score}/10")

        if scores:
            consensus["average_score"] = sum(scores) / len(scores)
            print(f"\n   📊 Consensus Score: {consensus['average_score']:.2f}/10")

        # 查找共识问题（两个工具都发现的问题）
        if (gemini_result["status"] in ["success", "partial"] and
            codex_result["status"] in ["success", "partial"]):

            gemini_issues = gemini_result["data"].get("critical_issues", [])
            codex_issues = codex_result["data"].get("critical_issues", [])

            print(f"\n   🔍 Analyzing consensus issues...")
            print(f"   Gemini found: {len(gemini_issues)} critical issues")
            print(f"   Codex found:  {len(codex_issues)} critical issues")

            # 简单的关键词匹配来查找共识
            consensus_issues = []
            for g_issue in gemini_issues:
                g_desc = str(g_issue).lower()
                for c_issue in codex_issues:
                    c_desc = str(c_issue).lower()
                    # 检查是否有共同的关键词
                    common_keywords = ["device", "gpu", "cuda", "hard-coded", "hardcoded",
                                     "eval", "train", "mode", "dropout", "error handling",
                                     "exception", "validation"]
                    for keyword in common_keywords:
                        if keyword in g_desc and keyword in c_desc:
                            consensus_issues.append({
                                "keyword": keyword,
                                "gemini_finding": g_issue,
                                "codex_finding": c_issue,
                                "priority": "HIGH"
                            })
                            break

            consensus["consensus_issues"] = consensus_issues
            print(f"   ✅ Found {len(consensus_issues)} consensus issues")

        # 保存报告
        report_file = self.output_dir / f"iteration_{iteration}_consensus.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(consensus, f, indent=2, ensure_ascii=False)

        # 生成可读报告
        readable_file = self.output_dir / f"iteration_{iteration}_consensus.md"
        self.generate_readable_consensus_report(consensus, readable_file)

        print(f"   💾 Report saved: {report_file}")

        return consensus

    def generate_readable_consensus_report(self, consensus: Dict[str, Any], output_file: Path):
        """生成可读的共识报告"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Cross-Review Consensus Report\n\n")
            f.write(f"**Iteration:** {consensus['iteration']}\n")
            f.write(f"**Generated:** {consensus['timestamp']}\n\n")

            f.write(f"## Quality Scores\n\n")
            if "gemini" in consensus["scores"]:
                f.write(f"- **Gemini Score:** {consensus['scores']['gemini']}/10\n")
            if "codex" in consensus["scores"]:
                f.write(f"- **Codex Score:** {consensus['scores']['codex']}/10\n")
            f.write(f"- **Average Score:** {consensus['average_score']:.2f}/10\n\n")

            if consensus["consensus_issues"]:
                f.write(f"## Consensus Issues ({len(consensus['consensus_issues'])})\n\n")
                f.write("These issues were identified by both AI tools:\n\n")

                for i, issue in enumerate(consensus["consensus_issues"], 1):
                    f.write(f"### {i}. {issue['keyword'].title()} Issue\n\n")
                    f.write(f"**Priority:** {issue['priority']}\n\n")
                    f.write(f"**Gemini Finding:**\n")
                    f.write(f"```\n{json.dumps(issue['gemini_finding'], indent=2)}\n```\n\n")
                    f.write(f"**Codex Finding:**\n")
                    f.write(f"```\n{json.dumps(issue['codex_finding'], indent=2)}\n```\n\n")

    async def apply_improvements(self, consensus: Dict[str, Any], iteration: int) -> bool:
        """应用改进（使用两个AI协同修改代码）"""
        self.print_banner(f"🔧 Applying Code Improvements - Iteration {iteration}")

        if not consensus["consensus_issues"]:
            print("   ℹ️  No consensus issues to fix")
            return False

        print(f"   📝 Found {len(consensus['consensus_issues'])} consensus issues to fix")

        # 为每个共识问题生成修复提示
        for i, issue in enumerate(consensus["consensus_issues"], 1):
            print(f"\n   Fixing issue {i}/{len(consensus['consensus_issues'])}: {issue['keyword']}")

            # 构建修复提示
            fix_prompt = f"""Fix the following issue in the codebase:

Issue: {issue['keyword']}

Gemini identified: {json.dumps(issue['gemini_finding'], indent=2)}
Codex identified: {json.dumps(issue['codex_finding'], indent=2)}

Please:
1. Locate the relevant files and lines
2. Apply the necessary fixes
3. Ensure the fix follows best practices
4. Preserve existing functionality

Make the changes directly to the files."""

            # 使用Codex进行修改（如果可用，使用workspace-write模式）
            try:
                result = subprocess.run(
                    ["codex", "exec", "--sandbox", "workspace-write", fix_prompt],
                    cwd=str(self.code_directory),
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                output = result.stdout + result.stderr

                if "upgrade to Plus" in output:
                    print(f"   ⚠️  Codex requires Plus subscription")
                    continue

                # 检查是否成功应用修改
                if "file update:" in output.lower() or "diff" in output.lower():
                    print(f"   ✅ Applied fix for: {issue['keyword']}")
                else:
                    print(f"   ⚠️  Fix may not have been applied for: {issue['keyword']}")

            except Exception as e:
                print(f"   ❌ Failed to apply fix: {e}")
                continue

        print(f"\n   🎉 Completed applying improvements")
        return True

    async def run_iteration(self, iteration: int, tools: Dict[str, bool]) -> Dict[str, Any]:
        """运行一次迭代"""
        self.print_banner(f"🔄 Iteration {iteration}/{self.max_iterations}", "=")

        # 运行两个工具的审阅
        gemini_result = {"status": "skipped", "tool": "gemini"}
        codex_result = {"status": "skipped", "tool": "codex"}

        if tools["gemini"]:
            gemini_result = self.run_gemini_review(iteration)

        if tools["codex"]:
            codex_result = self.run_codex_review(iteration)

        # 生成共识报告
        consensus = self.generate_consensus_report(gemini_result, codex_result, iteration)

        # 保存到历史
        self.review_history.append(consensus)

        # 检查是否达到目标
        if consensus["average_score"] >= self.target_score:
            print(f"\n   🎯 Target score {self.target_score} reached!")
            return consensus

        # 如果未达到目标且不是最后一次迭代，应用改进
        if iteration < self.max_iterations:
            improvements_applied = await self.apply_improvements(consensus, iteration)
            if not improvements_applied:
                print(f"\n   ℹ️  No improvements to apply")

        return consensus

    async def run(self):
        """运行完整的迭代改进流程"""
        self.print_banner("🚀 Starting Iterative Code Improvement Workflow", "=")

        print(f"📁 Code Directory: {self.code_directory}")
        print(f"🎯 Target Score: {self.target_score}/10")
        print(f"🔄 Max Iterations: {self.max_iterations}")

        # 检查工具可用性
        tools = self.check_tools_available()
        if not tools["gemini"] and not tools["codex"]:
            print("\n❌ Cannot proceed without review tools")
            return

        # 迭代改进
        for iteration in range(1, self.max_iterations + 1):
            consensus = await self.run_iteration(iteration, tools)

            if consensus["average_score"] >= self.target_score:
                break

            if iteration < self.max_iterations:
                print(f"\n   ⏳ Waiting 5 seconds before next iteration...")
                await asyncio.sleep(5)

        # 生成最终报告
        self.generate_final_report()

    def generate_final_report(self):
        """生成最终报告"""
        self.print_banner("📊 Final Report", "=")

        if not self.review_history:
            print("No review history available")
            return

        # 分数趋势
        print("\n📈 Score Progress:")
        for i, review in enumerate(self.review_history, 1):
            score = review["average_score"]
            status = "✅ TARGET REACHED" if score >= self.target_score else "🔄 In Progress"
            print(f"   Iteration {i}: {score:.2f}/10 - {status}")

        final_score = self.review_history[-1]["average_score"]
        improvement = final_score - self.review_history[0]["average_score"]

        print(f"\n🎯 Final Score: {final_score:.2f}/10")
        print(f"📊 Total Improvement: {improvement:+.2f} points")

        if final_score >= self.target_score:
            print(f"✅ Successfully reached target score of {self.target_score}/10!")
        else:
            print(f"⚠️  Did not reach target score (current: {final_score:.2f}, target: {self.target_score})")
            print(f"   Consider running more iterations or adjusting target")

        # 保存完整历史
        history_file = self.output_dir / "complete_history.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(self.review_history, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Complete history saved: {history_file}")
        print(f"📁 All reports saved in: {self.output_dir}")


async def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python iterative_code_improvement.py <code_directory> [target_score] [max_iterations]")
        print("\nExample:")
        print("  python iterative_code_improvement.py deepcode_lab/papers/1/generate_code 8.0 5")
        sys.exit(1)

    code_directory = sys.argv[1]
    target_score = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    improver = IterativeCodeImprover(
        code_directory=code_directory,
        target_score=target_score,
        max_iterations=max_iterations
    )

    await improver.run()


if __name__ == "__main__":
    asyncio.run(main())
