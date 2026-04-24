"""Tests for observe command - seamless observability instrumentation."""

import ast
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_observability_toolkit.cli.observe import (
    SkillAnalysisResult,
    SkillCodeAnalyzer,
    SkillObserver,
)


class TestSkillCodeAnalyzer:
    """Test SkillCodeAnalyzer"""

    def test_analyze_basic_function(self):
        """测试分析基本函数"""
        code = '''
def process_data(input_path: str, options: dict) -> dict:
    """
    Process input data with options.

    Args:
        input_path: Path to input file
        options: Processing options
    Returns:
        Processed result
    """
    with open(input_path, 'r') as f:
        content = f.read()
    return {"result": content}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analyzer = SkillCodeAnalyzer()
            result = analyzer.analyze(temp_path.parent, entry_point="process_data")

            assert result.entry_point == "process_data"
            assert result.description == "Process input data with options."
            assert len(result.inputs) == 2
            assert result.inputs[0]["name"] == "input_path"
            assert result.inputs[0]["type"] == "string"
            assert result.inputs[1]["name"] == "options"
            assert result.inputs[1]["type"] == "json"
            assert len(result.outputs) == 1
            assert result.outputs[0]["name"] == "result"
        finally:
            temp_path.unlink()

    def test_analyze_with_open_file(self):
        """测试检测文件操作工具"""
        code = '''
def read_file(path: str) -> str:
    """Read file content."""
    with open(path, 'r') as f:
        return f.read()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analyzer = SkillCodeAnalyzer()
            result = analyzer.analyze(temp_path.parent)

            assert "read_file" in result.tools_used
        finally:
            temp_path.unlink()

    def test_analyze_with_requests(self):
        """测试检测网络请求工具"""
        code = '''
import requests

def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    resp = requests.get(url)
    return resp.json()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analyzer = SkillCodeAnalyzer()
            result = analyzer.analyze(temp_path.parent)

            assert "web_search" in result.tools_used
        finally:
            temp_path.unlink()

    def test_analyze_no_python_files(self):
        """测试无 Python 文件情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SkillCodeAnalyzer()
            with pytest.raises(ValueError, match="未找到 Python 文件"):
                analyzer.analyze(Path(tmpdir))

    def test_analyze_auto_detect_entry_point(self):
        """测试自动检测入口函数"""
        code = '''
def execute(query: str) -> str:
    """Execute query."""
    return query.upper()

def helper(x):
    return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analyzer = SkillCodeAnalyzer()
            result = analyzer.analyze(temp_path.parent)

            assert result.entry_point == "execute"
        finally:
            temp_path.unlink()


class TestSkillAnalysisResult:
    """Test SkillAnalysisResult"""

    def test_to_skill_yaml(self):
        """测试生成 skill.yaml"""
        result = SkillAnalysisResult(
            entry_point="process",
            inputs=[{"name": "input", "type": "string", "required": True, "description": "input param"}],
            outputs=[{"name": "output", "type": "string", "description": "result", "guaranteed": True}],
            description="Process input data",
            tools_used=["read_file"],
            file_path="/tmp/main.py",
        )

        yaml_dict = result.to_skill_yaml()

        assert yaml_dict["sop"] == "1.0.0"
        assert yaml_dict["name"] == "main"
        assert yaml_dict["version"] == "0.1.0"
        assert yaml_dict["description"] == "Process input data"
        assert yaml_dict["inputs"] == result.inputs
        assert yaml_dict["outputs"] == result.outputs
        assert yaml_dict["tools_used"] == result.tools_used
        assert yaml_dict["observability"]["level"] == "L2"
        assert yaml_dict["observability"]["langfuse_integration"] is True

    def test_to_text(self):
        """测试生成文本输出"""
        result = SkillAnalysisResult(
            entry_point="process",
            inputs=[],
            outputs=[],
            description="Test",
            tools_used=[],
            file_path="/tmp/main.py",
        )

        text = result.to_text()

        assert "Entry Point: process" in text
        assert "Description: Test" in text
        assert "/tmp/main.py" in text


class TestSkillObserver:
    """Test SkillObserver"""

    def test_instrument_with_decorator(self):
        """测试注入追踪装饰器"""
        code = '''
def process(data: str) -> str:
    """Process data."""
    return data.upper()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.py"
            main_file.write_text(code)

            result = SkillAnalysisResult(
                entry_point="process",
                inputs=[],
                outputs=[],
                description="Test",
                tools_used=[],
                file_path=str(main_file),
            )

            observer = SkillObserver()
            output_path = Path(tmpdir) / "process_instrumented.py"

            observer._create_instrumented_file(
                original_path=str(main_file),
                output_path=output_path,
                entry_point="process",
            )

            assert output_path.exists()
            content = output_path.read_text()
            assert "@trace_skill_execution" in content

    def test_instrument_preserves_existing_decorator(self):
        """测试保留已有装饰器"""
        code = '''
from skill_observability_toolkit import trace_skill_execution

@trace_skill_execution(skill_name="test")
def process(data: str) -> str:
    """Process data."""
    return data.upper()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.py"
            main_file.write_text(code)

            result = SkillAnalysisResult(
                entry_point="process",
                inputs=[],
                outputs=[],
                description="Test",
                tools_used=[],
                file_path=str(main_file),
            )

            observer = SkillObserver(verbose=False)
            output_path = Path(tmpdir) / "process_instrumented.py"

            with patch('typer.echo'):
                observer._create_instrumented_file(
                    original_path=str(main_file),
                    output_path=output_path,
                    entry_point="process",
                )

            assert output_path.exists()
            content = output_path.read_text()
            assert content.count("@trace_skill_execution") == 1

    def test_instrument_generates_skill_yaml(self):
        """测试生成 skill.yaml"""
        code = '''
def process(data: str) -> str:
    """Process data."""
    return data.upper()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.py"
            main_file.write_text(code)

            result = SkillAnalysisResult(
                entry_point="process",
                inputs=[{"name": "data", "type": "string", "required": True, "description": "input"}],
                outputs=[{"name": "result", "type": "string", "description": "output", "guaranteed": True}],
                description="Process data",
                tools_used=["unknown"],
                file_path=str(main_file),
            )

            observer = SkillObserver()
            observer.instrument(
                skill_path=Path(tmpdir),
                analysis=result,
                output_dir=None,
                force=True,
            )

            skill_yaml = Path(tmpdir) / "skill.yaml"
            assert skill_yaml.exists()

            import yaml
            with open(skill_yaml) as f:
                yaml_content = yaml.safe_load(f)

            assert yaml_content["name"] == "main"
            assert yaml_content["sop"] == "1.0.0"

    def test_instrument_with_langfuse(self):
        """测试生成 .env.example"""
        code = '''
def process(data: str) -> str:
    """Process data."""
    return data.upper()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = Path(tmpdir) / "main.py"
            main_file.write_text(code)

            result = SkillAnalysisResult(
                entry_point="process",
                inputs=[],
                outputs=[],
                description="Test",
                tools_used=[],
                file_path=str(main_file),
            )

            observer = SkillObserver(langfuse_enabled=True)
            observer.instrument(
                skill_path=Path(tmpdir),
                analysis=result,
                output_dir=None,
                force=True,
            )

            env_example = Path(tmpdir) / ".env.example"
            assert env_example.exists()
            content = env_example.read_text()
            assert "LANGFUSE_PUBLIC_KEY" in content
            assert "LANGFUSE_SECRET_KEY" in content


class TestTypeInference:
    """Test type inference"""

    def test_infer_string_type(self):
        """测试字符串类型推断"""
        analyzer = SkillCodeAnalyzer()
        assert analyzer._infer_type("str") == "string"
        assert analyzer._infer_type("String") == "string"

    def test_infer_integer_type(self):
        """测试整数类型推断"""
        analyzer = SkillCodeAnalyzer()
        assert analyzer._infer_type("int") == "integer"
        assert analyzer._infer_type("Integer") == "integer"

    def test_infer_path_type(self):
        """测试路径类型推断"""
        analyzer = SkillCodeAnalyzer()
        assert analyzer._infer_type("Path") == "file_path"

    def test_infer_unknown_type(self):
        """测试未知类型推断"""
        analyzer = SkillCodeAnalyzer()
        assert analyzer._infer_type("UnknownType") == "string"


class TestGetTypeName:
    """Test type name extraction"""

    def test_get_simple_type(self):
        """测试简单类型"""
        analyzer = SkillCodeAnalyzer()
        tree = ast.parse("x: str")
        node = tree.body[0]
        assert analyzer._get_type_name(node.annotation) == "str"

    def test_get_subscript_type(self):
        """测试泛型类型"""
        analyzer = SkillCodeAnalyzer()
        tree = ast.parse("x: list[str]")
        node = tree.body[0]
        assert analyzer._get_type_name(node.annotation) == "list[str]"
