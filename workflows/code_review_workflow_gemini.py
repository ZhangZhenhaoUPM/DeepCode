"""
Code Review Workflow using Gemini 2.5 Pro

This workflow reviews generated code using Google's Gemini 2.5 Pro model for:
- Code quality assessment
- Best practices compliance
- Bug detection
- Performance optimization suggestions
- Documentation completeness
"""

import asyncio
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import AsyncOpenAI


class CodeReviewWorkflowGemini:
    """Code review workflow powered by Gemini 2.5 Pro"""

    def __init__(self, config_path: str = "mcp_agent.config.yaml"):
        """Initialize code review workflow"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Load configuration
        self.api_config = self._load_api_config(config_path)
        self.gemini_config = self.api_config.get("openai", {})
        self.model_name = self.gemini_config.get("default_model", "gemini-2.5-pro")

        # Initialize Gemini client (via OpenAI-compatible API)
        self.client = None

    def _load_api_config(self, config_path: str) -> Dict[str, Any]:
        """Load API configuration from YAML file"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to load API config: {e}")

    async def _initialize_gemini_client(self) -> AsyncOpenAI:
        """Initialize Gemini client through OpenAI-compatible API"""
        # Check if secrets file exists for API key
        secrets_path = "mcp_agent.secrets.yaml"
        api_key = None

        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                secrets = yaml.safe_load(f)
                api_key = secrets.get("openai", {}).get("api_key", "")
        except Exception as e:
            self.logger.warning(f"Could not load secrets file: {e}")

        if not api_key or api_key.strip() == "":
            raise ValueError("Gemini API key not found in mcp_agent.secrets.yaml")

        # Get base URL for Gemini (Google AI Studio)
        base_url = self.gemini_config.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        self.logger.info(f"✅ Gemini client initialized: {self.model_name}")
        return client

    async def review_code_file(self, file_path: str, context: str = "") -> Dict[str, Any]:
        """
        Review a single code file

        Args:
            file_path: Path to the code file to review
            context: Additional context about the file (e.g., purpose, related files)

        Returns:
            Dict containing review results
        """
        if not self.client:
            self.client = await self._initialize_gemini_client()

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()
        except Exception as e:
            return {
                "file": file_path,
                "status": "error",
                "error": f"Failed to read file: {e}"
            }

        # Construct review prompt
        review_prompt = self._build_review_prompt(file_path, code_content, context)

        # Call Gemini API
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer with deep knowledge of software engineering best practices, security, performance optimization, and maintainability."
                    },
                    {
                        "role": "user",
                        "content": review_prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more focused, analytical reviews
                max_tokens=self.gemini_config.get("base_max_tokens", 20000)
            )

            review_content = response.choices[0].message.content

            return {
                "file": file_path,
                "status": "success",
                "review": review_content,
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to review {file_path}: {e}")
            return {
                "file": file_path,
                "status": "error",
                "error": str(e)
            }

    def _build_review_prompt(self, file_path: str, code_content: str, context: str) -> str:
        """Build comprehensive code review prompt"""
        return f"""Please perform a comprehensive code review of the following file:

**File**: `{file_path}`
**Context**: {context if context else "No additional context provided"}

**Code**:
```
{code_content}
```

Please provide a detailed review covering:

1. **Code Quality** (0-10):
   - Readability and maintainability
   - Coding style and conventions
   - Complexity assessment

2. **Correctness** (0-10):
   - Logic errors and bugs
   - Edge case handling
   - Type safety and error handling

3. **Performance** (0-10):
   - Algorithmic efficiency
   - Resource usage
   - Potential bottlenecks

4. **Security** (0-10):
   - Security vulnerabilities
   - Input validation
   - Data handling safety

5. **Best Practices** (0-10):
   - Design patterns usage
   - SOLID principles
   - Python/language-specific idioms

6. **Documentation** (0-10):
   - Docstrings and comments quality
   - Code self-documentation
   - API documentation

7. **Specific Issues**: List any bugs, anti-patterns, or concerns

8. **Recommendations**: Concrete improvement suggestions

9. **Overall Score**: Average of above scores

Please provide your review in the following JSON format:

```json
{{
  "overall_score": <average_score>,
  "scores": {{
    "code_quality": <score>,
    "correctness": <score>,
    "performance": <score>,
    "security": <score>,
    "best_practices": <score>,
    "documentation": <score>
  }},
  "issues": [
    {{
      "severity": "critical|high|medium|low",
      "category": "bug|security|performance|style",
      "line": <line_number or null>,
      "description": "...",
      "suggestion": "..."
    }}
  ],
  "strengths": ["..."],
  "recommendations": ["..."],
  "summary": "..."
}}
```"""

    async def review_directory(
        self,
        directory_path: str,
        file_pattern: str = "*.py",
        exclude_patterns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Review all code files in a directory

        Args:
            directory_path: Path to directory containing code
            file_pattern: Glob pattern for files to review
            exclude_patterns: List of patterns to exclude

        Returns:
            Dict containing aggregated review results
        """
        if exclude_patterns is None:
            exclude_patterns = ["**/test_*.py", "**/__pycache__/**", "**/.*"]

        directory = Path(directory_path)
        if not directory.exists():
            return {
                "status": "error",
                "error": f"Directory not found: {directory_path}"
            }

        # Find all matching files
        all_files = list(directory.rglob(file_pattern))

        # Filter out excluded patterns
        files_to_review = []
        for file_path in all_files:
            should_exclude = False
            for pattern in exclude_patterns:
                if file_path.match(pattern):
                    should_exclude = True
                    break
            if not should_exclude:
                files_to_review.append(file_path)

        self.logger.info(f"📁 Found {len(files_to_review)} files to review in {directory_path}")

        # Review each file
        reviews = []
        for file_path in files_to_review:
            self.logger.info(f"🔍 Reviewing: {file_path.name}")
            review = await self.review_code_file(str(file_path))
            reviews.append(review)

            # Add small delay to avoid rate limiting
            await asyncio.sleep(1)

        # Aggregate results
        return self._aggregate_reviews(reviews, directory_path)

    def _aggregate_reviews(self, reviews: List[Dict[str, Any]], directory_path: str) -> Dict[str, Any]:
        """Aggregate individual file reviews into summary report"""
        successful_reviews = [r for r in reviews if r["status"] == "success"]
        failed_reviews = [r for r in reviews if r["status"] == "error"]

        # Parse scores from reviews
        all_scores = []
        all_issues = []

        for review in successful_reviews:
            try:
                # Try to extract JSON from review content
                review_content = review["review"]

                # Find JSON block in the review
                json_start = review_content.find("{")
                json_end = review_content.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = review_content[json_start:json_end]
                    review_data = json.loads(json_str)

                    if "overall_score" in review_data:
                        all_scores.append(review_data["overall_score"])

                    if "issues" in review_data:
                        all_issues.extend(review_data["issues"])
            except Exception as e:
                self.logger.warning(f"Could not parse review JSON for {review['file']}: {e}")

        # Calculate aggregate scores
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        # Count issues by severity
        critical_count = len([i for i in all_issues if i.get("severity") == "critical"])
        high_count = len([i for i in all_issues if i.get("severity") == "high"])
        medium_count = len([i for i in all_issues if i.get("severity") == "medium"])
        low_count = len([i for i in all_issues if i.get("severity") == "low"])

        return {
            "directory": directory_path,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name,
            "summary": {
                "total_files": len(reviews),
                "reviewed_successfully": len(successful_reviews),
                "review_failed": len(failed_reviews),
                "average_score": round(avg_score, 2),
                "total_issues": len(all_issues),
                "critical_issues": critical_count,
                "high_issues": high_count,
                "medium_issues": medium_count,
                "low_issues": low_count
            },
            "reviews": reviews
        }

    async def generate_review_report(
        self,
        review_results: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a formatted review report

        Args:
            review_results: Results from review_directory()
            output_path: Optional path to save the report

        Returns:
            Formatted report as markdown string
        """
        report_lines = []

        # Header
        report_lines.append(f"# Code Review Report")
        report_lines.append(f"\n**Generated**: {review_results['timestamp']}")
        report_lines.append(f"**Model**: {review_results['model']}")
        report_lines.append(f"**Directory**: {review_results['directory']}\n")

        # Summary
        summary = review_results["summary"]
        report_lines.append("## Summary\n")
        report_lines.append(f"- **Total Files**: {summary['total_files']}")
        report_lines.append(f"- **Successfully Reviewed**: {summary['reviewed_successfully']}")
        report_lines.append(f"- **Failed Reviews**: {summary['review_failed']}")
        report_lines.append(f"- **Average Score**: {summary['average_score']}/10")
        report_lines.append(f"- **Total Issues**: {summary['total_issues']}")
        report_lines.append(f"  - Critical: {summary['critical_issues']}")
        report_lines.append(f"  - High: {summary['high_issues']}")
        report_lines.append(f"  - Medium: {summary['medium_issues']}")
        report_lines.append(f"  - Low: {summary['low_issues']}\n")

        # Individual file reviews
        report_lines.append("## Detailed Reviews\n")

        for review in review_results["reviews"]:
            if review["status"] == "success":
                report_lines.append(f"### {review['file']}\n")
                report_lines.append(review["review"])
                report_lines.append("\n---\n")
            else:
                report_lines.append(f"### {review['file']} ❌\n")
                report_lines.append(f"**Error**: {review['error']}\n")
                report_lines.append("\n---\n")

        report = "\n".join(report_lines)

        # Save to file if output_path provided
        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report)
                self.logger.info(f"✅ Report saved to: {output_path}")
            except Exception as e:
                self.logger.error(f"Failed to save report: {e}")

        return report


async def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python code_review_workflow_gemini.py <directory_path>")
        print("Example: python code_review_workflow_gemini.py deepcode_lab/papers/9/generate_code")
        sys.exit(1)

    directory_path = sys.argv[1]

    # Initialize workflow
    workflow = CodeReviewWorkflowGemini()

    # Review directory
    print(f"\n🔍 Starting code review for: {directory_path}")
    print(f"📝 Using model: {workflow.model_name}\n")

    results = await workflow.review_directory(directory_path)

    # Generate report
    output_path = Path(directory_path).parent / "code_review_report.md"
    report = await workflow.generate_review_report(results, str(output_path))

    # Print summary
    print(f"\n✅ Code review completed!")
    print(f"\n📊 Summary:")
    print(f"   - Files reviewed: {results['summary']['reviewed_successfully']}/{results['summary']['total_files']}")
    print(f"   - Average score: {results['summary']['average_score']}/10")
    print(f"   - Total issues: {results['summary']['total_issues']}")
    print(f"   - Report saved: {output_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
