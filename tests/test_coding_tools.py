"""
Tests for TESS Coding Tools — validates all tool functions in isolation.
Uses a temporary directory for file operations.
"""

import os
import sys
import tempfile
import shutil
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tess_cli.core.coding_tools import CodingTools
from tess_cli.core.tess_md import find_tess_md, read_tess_md


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace with test files."""
    # Create test files
    (tmp_path / "hello.py").write_text("def hello():\n    print('Hello World')\n\nhello()\n")
    (tmp_path / "README.md").write_text("# Test Project\n## Setup\nInstall deps\n## Usage\nRun it\n")
    (tmp_path / "data.txt").write_text("line one\nline two\nline three\nline four\nline five\n")

    # Create a subdirectory
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "main.py").write_text("import os\nimport sys\n\nclass App:\n    def run(self):\n        pass\n")
    (sub / "utils.py").write_text("import subprocess\n\ndef helper():\n    return True\n")

    return tmp_path


@pytest.fixture
def tools(workspace):
    """Create CodingTools bound to the temp workspace."""
    return CodingTools(str(workspace))


# ─── read_file ────────────────────────────────────────────────────────────────

class TestReadFile:
    def test_read_full_file(self, tools):
        result = tools.read_file("hello.py")
        assert "def hello():" in result
        assert "Hello World" in result

    def test_read_line_range(self, tools):
        result = tools.read_file("data.txt", start_line=2, end_line=4)
        assert "line two" in result
        assert "line three" in result
        assert "line four" in result
        assert "line one" not in result

    def test_read_missing_file(self, tools):
        result = tools.read_file("nonexistent.py")
        assert "Error" in result

    def test_read_subdirectory_file(self, tools):
        result = tools.read_file("src/main.py")
        assert "class App" in result


# ─── write_file ───────────────────────────────────────────────────────────────

class TestWriteFile:
    def test_write_new_file(self, tools, workspace):
        result = tools.write_file("new_file.py", "print('new')\n")
        assert "✅" in result
        assert (workspace / "new_file.py").exists()
        assert (workspace / "new_file.py").read_text() == "print('new')\n"

    def test_write_creates_directories(self, tools, workspace):
        result = tools.write_file("deep/nested/file.py", "# deep\n")
        assert "✅" in result
        assert (workspace / "deep" / "nested" / "file.py").exists()

    def test_write_overwrites(self, tools, workspace):
        tools.write_file("hello.py", "# overwritten\n")
        content = (workspace / "hello.py").read_text()
        assert content == "# overwritten\n"


# ─── edit_file ────────────────────────────────────────────────────────────────

class TestEditFile:
    def test_exact_match_edit(self, tools, workspace):
        result = tools.edit_file("hello.py", "print('Hello World')", "print('Hello TESS')")
        assert "✅" in result
        content = (workspace / "hello.py").read_text()
        assert "Hello TESS" in content
        assert "Hello World" not in content

    def test_search_not_found(self, tools):
        result = tools.edit_file("hello.py", "NONEXISTENT_TEXT", "replacement")
        assert "Error" in result

    def test_edit_missing_file(self, tools):
        result = tools.edit_file("missing.py", "x", "y")
        assert "Error" in result


# ─── list_dir ─────────────────────────────────────────────────────────────────

class TestListDir:
    def test_list_root(self, tools):
        result = tools.list_dir(".")
        assert "hello.py" in result
        assert "README.md" in result
        assert "src" in result

    def test_list_subdir(self, tools):
        result = tools.list_dir("src")
        assert "main.py" in result
        assert "utils.py" in result

    def test_list_missing(self, tools):
        result = tools.list_dir("nonexistent")
        assert "Error" in result


# ─── grep_search ──────────────────────────────────────────────────────────────

class TestGrepSearch:
    def test_search_pattern(self, tools):
        result = tools.grep_search("import", ".")
        assert "src" in result  # Should find imports in src/main.py and src/utils.py

    def test_search_with_extension_filter(self, tools):
        result = tools.grep_search("import", ".", extensions=[".py"])
        assert ".py" in result

    def test_search_no_match(self, tools):
        result = tools.grep_search("ZZZZNOTFOUND", ".")
        assert "No matches" in result

    def test_search_missing_path(self, tools):
        result = tools.grep_search("test", "nonexistent_dir")
        assert "Error" in result


# ─── file_outline ─────────────────────────────────────────────────────────────

class TestFileOutline:
    def test_python_outline(self, tools):
        result = tools.file_outline("src/main.py")
        assert "class App" in result

    def test_markdown_outline(self, tools):
        result = tools.file_outline("README.md")
        assert "# Test Project" in result
        assert "## Setup" in result

    def test_outline_missing_file(self, tools):
        result = tools.file_outline("missing.py")
        assert "Error" in result

    def test_python_function_outline(self, tools):
        result = tools.file_outline("hello.py")
        assert "hello" in result


# ─── run_command ──────────────────────────────────────────────────────────────

class TestRunCommand:
    def test_run_simple_command(self, tools):
        result = tools.run_command("echo hello_tess")
        assert "hello_tess" in result

    def test_empty_command(self, tools):
        result = tools.run_command("")
        assert "Error" in result


# ─── tess_md ──────────────────────────────────────────────────────────────────

class TestTessMD:
    def test_find_tess_md_exists(self, workspace):
        (workspace / "TESS.md").write_text("# Rules\nUse snake_case\n")
        path = find_tess_md(str(workspace))
        assert path is not None
        assert path.endswith("TESS.md")

    def test_find_tess_md_missing(self, tmp_path):
        path = find_tess_md(str(tmp_path))
        assert path is None

    def test_find_tess_md_in_parent(self, workspace):
        (workspace / "TESS.md").write_text("# Root Rules\n")
        sub = workspace / "src"
        path = find_tess_md(str(sub))
        assert path is not None

    def test_read_tess_md(self, workspace):
        (workspace / "TESS.md").write_text("Use PEP8\n")
        content = read_tess_md(str(workspace))
        assert "PEP8" in content

    def test_read_tess_md_missing(self, tmp_path):
        content = read_tess_md(str(tmp_path))
        assert content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
