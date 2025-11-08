"""
File processing utilities for handling paper files and related operations.
"""

import json
import os
import re
from typing import Dict, List, Optional, Union


class FileProcessor:
    """
    A class to handle file processing operations including path extraction and file reading.
    """

    @staticmethod
    def extract_file_path(file_info: Union[str, Dict]) -> Optional[str]:
        """
        Extract paper directory path from the input information.

        Args:
            file_info: Either a JSON string or a dictionary containing file information

        Returns:
            Optional[str]: The extracted paper directory path or None if not found
        """
        try:
            # Handle direct file path input
            if isinstance(file_info, str):
                # Check if it's a file path (existing or not)
                if file_info.endswith(
                    (".md", ".pdf", ".txt", ".docx", ".doc", ".html", ".htm")
                ):
                    # It's a file path, return the directory
                    return os.path.dirname(os.path.abspath(file_info))
                elif os.path.exists(file_info):
                    if os.path.isfile(file_info):
                        return os.path.dirname(os.path.abspath(file_info))
                    elif os.path.isdir(file_info):
                        return os.path.abspath(file_info)

                # Try to parse as JSON
                try:
                    info_dict = json.loads(file_info)
                except json.JSONDecodeError:
                    # 尝试从文本中提取JSON
                    info_dict = FileProcessor.extract_json_from_text(file_info)
                    if not info_dict:
                        # If not JSON and doesn't look like a file path, raise error
                        raise ValueError(
                            f"Input is neither a valid file path nor JSON: {file_info}"
                        )
            else:
                info_dict = file_info

            # Extract paper path from dictionary (support both 'paper_path' and 'path')
            paper_path = info_dict.get("paper_path") or info_dict.get("path")
            print(f"\n🔍 DEBUG extract_file_path:")
            print(f"  info_dict keys: {list(info_dict.keys())}")
            print(f"  info_dict: {info_dict}")
            print(f"  paper_path: {paper_path}")

            # If paper_path is None or empty, try to find the moved file in deepcode_lab
            if not paper_path or paper_path == "None":
                print("  ⚠️ paper_path is None, searching for moved file...")
                # Look in deepcode_lab/papers directory
                deepcode_lab = os.path.join(os.getcwd(), "deepcode_lab", "papers")
                if os.path.exists(deepcode_lab):
                    # Find the most recently created directory
                    dirs = [d for d in os.listdir(deepcode_lab) if os.path.isdir(os.path.join(deepcode_lab, d))]
                    if dirs:
                        # Sort by modification time, get the newest
                        dirs.sort(key=lambda d: os.path.getmtime(os.path.join(deepcode_lab, d)), reverse=True)
                        newest_dir = os.path.join(deepcode_lab, dirs[0])
                        # Look for .md file in this directory
                        for file in os.listdir(newest_dir):
                            if file.endswith('.md'):
                                paper_path = os.path.join(newest_dir, file)
                                print(f"  ✅ Found moved file: {paper_path}")
                                break

            if not paper_path or paper_path == "None":
                raise ValueError(f"No paper_path or path found in input dictionary. Keys found: {list(info_dict.keys())}, Dict: {info_dict}")

            # Get the directory path instead of the file path
            paper_dir = os.path.dirname(paper_path)

            # Convert to absolute path if relative
            if not os.path.isabs(paper_dir):
                paper_dir = os.path.abspath(paper_dir)

            return paper_dir

        except (AttributeError, TypeError) as e:
            raise ValueError(f"Invalid input format: {str(e)}")

    @staticmethod
    def find_markdown_file(directory: str) -> Optional[str]:
        """
        Find the first markdown file in the given directory.

        Args:
            directory: Directory path to search

        Returns:
            Optional[str]: Path to the markdown file or None if not found
        """
        if not os.path.isdir(directory):
            return None

        for file in os.listdir(directory):
            if file.endswith(".md"):
                return os.path.join(directory, file)
        return None

    @staticmethod
    def parse_markdown_sections(content: str) -> List[Dict[str, Union[str, int, List]]]:
        """
        Parse markdown content and organize it by sections based on headers.

        Args:
            content: The markdown content to parse

        Returns:
            List[Dict]: A list of sections, each containing:
                - level: The header level (1-6)
                - title: The section title
                - content: The section content
                - subsections: List of subsections
        """
        # Split content into lines
        lines = content.split("\n")
        sections = []
        current_section = None
        current_content = []

        for line in lines:
            # Check if line is a header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                # If we were building a section, save its content
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start a new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    "level": level,
                    "title": title,
                    "content": "",
                    "subsections": [],
                }
                current_content = []
            elif current_section is not None:
                current_content.append(line)

        # Don't forget to save the last section
        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)

        return FileProcessor._organize_sections(sections)

    @staticmethod
    def _organize_sections(sections: List[Dict]) -> List[Dict]:
        """
        Organize sections into a hierarchical structure based on their levels.

        Args:
            sections: List of sections with their levels

        Returns:
            List[Dict]: Organized hierarchical structure of sections
        """
        result = []
        section_stack = []

        for section in sections:
            while section_stack and section_stack[-1]["level"] >= section["level"]:
                section_stack.pop()

            if section_stack:
                section_stack[-1]["subsections"].append(section)
            else:
                result.append(section)

            section_stack.append(section)

        return result

    @staticmethod
    async def read_file_content(file_path: str) -> str:
        """
        Read the content of a file asynchronously.

        Args:
            file_path: Path to the file to read

        Returns:
            str: The content of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        try:
            # Ensure the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check if file is actually a PDF by reading the first few bytes
            with open(file_path, "rb") as f:
                header = f.read(8)
                if header.startswith(b"%PDF"):
                    # Auto-convert PDF to markdown
                    print(f"📄 Detected PDF file, converting to markdown: {file_path}")
                    try:
                        from tools.pdf_downloader import DoclingConverter

                        converter = DoclingConverter()

                        # Convert PDF to markdown in the same directory
                        md_path = file_path.replace('.pdf', '.md')

                        # Use DoclingConverter to convert
                        result = converter.convert_to_markdown(file_path, md_path)

                        print(f"✅ PDF converted to markdown: {md_path}")
                        print(f"   Conversion result: {result}")

                        # Update file_path to point to the markdown file
                        file_path = md_path
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        raise IOError(
                            f"Failed to convert PDF {file_path} to markdown: {str(e)}"
                        )

            # Read file content
            # Note: Using async with would be better for large files
            # but for simplicity and compatibility, using regular file reading
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return content

        except UnicodeDecodeError as e:
            raise IOError(
                f"Error reading file {file_path}: File encoding is not UTF-8. Original error: {str(e)}"
            )
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {str(e)}")

    @staticmethod
    def format_section_content(section: Dict) -> str:
        """
        Format a section's content with standardized spacing and structure.

        Args:
            section: Dictionary containing section information

        Returns:
            str: Formatted section content
        """
        # Start with section title
        formatted = f"\n{'#' * section['level']} {section['title']}\n"

        # Add section content if it exists
        if section["content"]:
            formatted += f"\n{section['content'].strip()}\n"

        # Process subsections
        if section["subsections"]:
            # Add a separator before subsections if there's content
            if section["content"]:
                formatted += "\n---\n"

            # Process each subsection
            for subsection in section["subsections"]:
                formatted += FileProcessor.format_section_content(subsection)

        # Add section separator
        formatted += "\n" + "=" * 80 + "\n"

        return formatted

    @staticmethod
    def standardize_output(sections: List[Dict]) -> str:
        """
        Convert structured sections into a standardized string format.

        Args:
            sections: List of section dictionaries

        Returns:
            str: Standardized string output
        """
        output = []

        # Process each top-level section
        for section in sections:
            output.append(FileProcessor.format_section_content(section))

        # Join all sections with clear separation
        return "\n".join(output)

    @classmethod
    async def process_file_input(
        cls, file_input: Union[str, Dict], base_dir: str = None
    ) -> Dict:
        """
        Process file input information and return the structured content.

        Args:
            file_input: File input information (JSON string, dict, or direct file path)
            base_dir: Optional base directory to use for creating paper directories (for sync support)

        Returns:
            Dict: The structured content with sections and standardized text
        """
        try:
            # 首先尝试从字符串中提取markdown文件路径
            if isinstance(file_input, str):
                import re

                file_path_match = re.search(r"`([^`]+\.md)`", file_input)
                if file_path_match:
                    paper_path = file_path_match.group(1)
                    file_input = {"paper_path": paper_path}

            # Extract paper directory path
            paper_dir = cls.extract_file_path(file_input)

            # If base_dir is provided, adjust paper_dir to be relative to base_dir
            if base_dir and paper_dir:
                # If paper_dir is using default location, move it to base_dir
                if paper_dir.endswith(("deepcode_lab", "agent_folders")):
                    paper_dir = base_dir
                else:
                    # Extract the relative part and combine with base_dir
                    paper_name = os.path.basename(paper_dir)
                    # 保持原始目录名不变，不做任何替换
                    paper_dir = os.path.join(base_dir, "papers", paper_name)

                # Ensure the directory exists
                os.makedirs(paper_dir, exist_ok=True)

            if not paper_dir:
                raise ValueError("Could not determine paper directory path")

            # Get the actual file path
            file_path = None
            if isinstance(file_input, str):
                # 尝试解析为JSON（处理下载结果）
                try:
                    parsed_json = json.loads(file_input)
                    if isinstance(parsed_json, dict) and ("paper_path" in parsed_json or "path" in parsed_json):
                        file_path = parsed_json.get("paper_path") or parsed_json.get("path")
                        # 如果文件不存在，尝试查找markdown文件
                        if file_path and not os.path.exists(file_path):
                            paper_dir = os.path.dirname(file_path)
                            if os.path.isdir(paper_dir):
                                file_path = cls.find_markdown_file(paper_dir)
                                if not file_path:
                                    raise ValueError(
                                        f"No markdown file found in directory: {paper_dir}"
                                    )
                    else:
                        raise ValueError("Invalid JSON format: missing paper_path or path")
                except json.JSONDecodeError:
                    # 尝试从文本中提取JSON（处理包含额外文本的下载结果）
                    extracted_json = cls.extract_json_from_text(file_input)
                    if extracted_json and ("paper_path" in extracted_json or "path" in extracted_json):
                        file_path = extracted_json.get("paper_path") or extracted_json.get("path")
                        # 如果文件不存在，尝试查找markdown文件
                        if file_path and not os.path.exists(file_path):
                            paper_dir = os.path.dirname(file_path)
                            if os.path.isdir(paper_dir):
                                file_path = cls.find_markdown_file(paper_dir)
                                if not file_path:
                                    raise ValueError(
                                        f"No markdown file found in directory: {paper_dir}"
                                    )
                    else:
                        # 不是JSON，按文件路径处理
                        # Check if it's a file path (existing or not)
                        if file_input.endswith(
                            (".md", ".pdf", ".txt", ".docx", ".doc", ".html", ".htm")
                        ):
                            if os.path.exists(file_input):
                                file_path = file_input
                            else:
                                # File doesn't exist, try to find markdown in the directory
                                file_path = cls.find_markdown_file(paper_dir)
                                if not file_path:
                                    raise ValueError(
                                        f"No markdown file found in directory: {paper_dir}"
                                    )
                        elif os.path.exists(file_input):
                            if os.path.isfile(file_input):
                                file_path = file_input
                            elif os.path.isdir(file_input):
                                # If it's a directory, find the markdown file
                                file_path = cls.find_markdown_file(file_input)
                                if not file_path:
                                    raise ValueError(
                                        f"No markdown file found in directory: {file_input}"
                                    )
                        else:
                            raise ValueError(f"Invalid input: {file_input}")
            else:
                # Dictionary input
                file_path = file_input.get("paper_path") or file_input.get("path")

                # If paper_path is None or doesn't exist, try to find markdown in the directory
                if not file_path or file_path == "None" or not os.path.exists(file_path):
                    # Use paper_dir that was already extracted (with fallback logic)
                    if os.path.isdir(paper_dir):
                        file_path = cls.find_markdown_file(paper_dir)
                        if file_path:
                            print(f"  ✅ Found markdown file in directory: {file_path}")
                        else:
                            raise ValueError(
                                f"No markdown file found in directory: {paper_dir}"
                            )
                    else:
                        raise ValueError(f"Invalid paper directory: {paper_dir}")

            if not file_path:
                raise ValueError("No valid file path found")

            # Read file content
            content = await cls.read_file_content(file_path)

            # Parse and structure the content
            structured_content = cls.parse_markdown_sections(content)

            # Generate standardized text output
            standardized_text = cls.standardize_output(structured_content)

            return {
                "paper_dir": paper_dir,
                "file_path": file_path,
                "sections": structured_content,
                "standardized_text": standardized_text,
            }

        except Exception as e:
            raise ValueError(f"Error processing file input: {str(e)}")

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict]:
        """
        Extract JSON from text that may contain markdown code blocks or other content.

        Args:
            text: Text that may contain JSON

        Returns:
            Optional[Dict]: Extracted JSON as dictionary or None if not found
        """
        import re

        # Try to find JSON in markdown code blocks first
        json_pattern = r"```json\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON in plain code blocks
        json_pattern = r"```\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find standalone JSON object (look for { ... } pattern)
        # Find all potential JSON objects in the text
        brace_count = 0
        start_idx = -1

        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # Found a complete JSON object
                    potential_json = text[start_idx:i+1]
                    try:
                        parsed = json.loads(potential_json)
                        if isinstance(parsed, dict):
                            # Check if it looks like our expected format
                            if "paper_path" in parsed or "status" in parsed or "path" in parsed:
                                return parsed
                    except json.JSONDecodeError:
                        # Continue looking for other JSON objects
                        pass
                    start_idx = -1

        # Last resort: try simple regex pattern
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and ("paper_path" in parsed or "path" in parsed or "status" in parsed):
                    return parsed
            except json.JSONDecodeError:
                continue

        return None
