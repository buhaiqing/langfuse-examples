"""CLI command for seamless observability instrumentation of existing Skills."""

import ast
from pathlib import Path

import typer
import yaml

app = typer.Typer(name="observe", help="无缝给传统 Agent Skill 加上可观测能力")


class SkillAnalysisResult:
    """代码分析结果"""

    def __init__(
        self,
        entry_point: str,
        inputs: list,
        outputs: list,
        description: str,
        tools_used: list,
        file_path: str,
    ):
        self.entry_point = entry_point
        self.inputs = inputs
        self.outputs = outputs
        self.description = description
        self.tools_used = tools_used
        self.file_path = file_path

    def to_text(self) -> str:
        return f"""Entry Point: {self.entry_point}
Description: {self.description}
Inputs: {self.inputs}
Outputs: {self.outputs}
Tools Used: {self.tools_used}
Source: {self.file_path}
"""

    def to_skill_yaml(self) -> dict:
        return {
            "sop": "1.0.0",
            "name": self._derive_name(),
            "version": "0.1.0",
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tools_used": self.tools_used,
            "observability": {
                "level": "L2",
                "langfuse_integration": True,
            },
        }

    def _derive_name(self) -> str:
        return Path(self.file_path).stem.replace("_", "-")


class SkillCodeAnalyzer:
    """Skill 代码分析器 - 使用 AST"""

    def analyze(self, skill_path: Path, entry_point: str | None = None) -> SkillAnalysisResult:
        """分析 Skill 代码"""
        py_files = list(skill_path.rglob("*.py"))
        if not py_files:
            raise ValueError(f"未找到 Python 文件: {skill_path}")

        main_file = self._find_main_file(py_files, entry_point)

        with open(main_file, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        target_func = self._find_entry_function(tree, entry_point)
        inputs = self._extract_inputs(target_func)
        outputs = self._extract_outputs(target_func)
        description = self._extract_description(target_func)
        tools = self._detect_tools(tree)

        return SkillAnalysisResult(
            entry_point=target_func.name,
            inputs=inputs,
            outputs=outputs,
            description=description,
            tools_used=tools,
            file_path=str(main_file),
        )

    def _find_main_file(self, py_files: list, entry_point: str | None) -> Path:
        """查找主文件"""
        if len(py_files) == 1:
            return py_files[0]

        candidates = [f for f in py_files if f.name in ("main.py", "skill.py", "__main__.py")]
        if candidates:
            return candidates[0]

        return py_files[0]

    def _find_entry_function(self, tree: ast.AST, entry_point: str | None) -> ast.FunctionDef:
        """查找入口函数"""
        for node in ast.walk(tree):  # type: ignore[attr-defined]
            if isinstance(node, ast.FunctionDef):
                if entry_point and node.name == entry_point:
                    return node
                if node.name in ("execute", "run", "main", "skill"):
                    return node
                if node.name.startswith("handle_") or node.name.startswith("process_"):
                    return node

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node

        raise ValueError(f"未找到入口函数: {entry_point}")

    def _extract_inputs(self, func: ast.FunctionDef) -> list:
        """提取输入参数"""
        inputs = []
        for arg in func.args.args:
            type_hint = ""
            if arg.annotation:
                type_hint = self._get_type_name(arg.annotation)

            inputs.append({
                "name": arg.arg,
                "type": self._infer_type(type_hint),
                "required": True,
                "description": f"{arg.arg} parameter",
            })

        return inputs

    def _extract_outputs(self, func: ast.FunctionDef) -> list:
        """提取输出信息"""
        if func.returns:
            return_type = self._get_type_name(func.returns)
        else:
            return_type = "dict"

        return [{
            "name": "result",
            "type": return_type,
            "description": "执行结果",
            "guaranteed": True,
        }]

    def _extract_description(self, func: ast.FunctionDef) -> str:
        """提取描述"""
        if ast.get_docstring(func):
            return ast.get_docstring(func).split("\n")[0]
        return f"{func.name} skill"

    def _detect_tools(self, tree: ast.AST) -> list:
        """检测使用的工具"""
        tools = set()
        tool_patterns = {
            "read_file": ["open", "read"],
            "web_search": ["requests", "urllib", "httpx"],
            "code_execution": ["exec", "eval", "subprocess"],
            "database": ["sql", "query"],
        }

        source = ast.unparse(tree)
        for tool, patterns in tool_patterns.items():
            if any(p in source for p in patterns):
                tools.add(tool)

        return list(tools) if tools else ["unknown"]

    def _get_type_name(self, node: ast.AST) -> str:
        """获取类型名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.Subscript):
            return f"{self._get_type_name(node.value)}[{self._get_type_name(node.slice)}]"
        elif isinstance(node, ast.BinOp):
            return "str"
        return "any"

    def _infer_type(self, type_hint: str) -> str:
        """推断类型"""
        type_map = {
            "str": "string",
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "array": "array",
            "dict": "json",
            "json": "json",
            "path": "file_path",
        }
        return type_map.get(type_hint.lower(), "string")


class SkillObserver:
    """Skill 观测化器"""

    def __init__(self, langfuse_enabled: bool = False, verbose: bool = False):
        self.langfuse_enabled = langfuse_enabled
        self.verbose = verbose

    def instrument(
        self,
        skill_path: Path,
        analysis: SkillAnalysisResult,
        output_dir: str | None,
        force: bool = False,
    ):
        """注入追踪代码"""
        output = Path(output_dir) if output_dir else skill_path

        skill_yaml_path = output / "skill.yaml"
        if skill_yaml_path.exists() and not force:
            typer.echo("⚠️ skill.yaml 已存在，使用 --force 覆盖", err=True)
            return

        skill_yaml_content = yaml.dump(
            analysis.to_skill_yaml(),
            allow_unicode=True,
            default_flow_style=False,
        )
        skill_yaml_path.write_text(skill_yaml_content, encoding="utf-8")

        if self.verbose:
            typer.echo(f"   生成: {skill_yaml_path}")

        instrumented_path = output / f"{analysis.entry_point}_instrumented.py"
        self._create_instrumented_file(
            original_path=analysis.file_path,
            output_path=instrumented_path,
            entry_point=analysis.entry_point,
            force=force,
        )

        if self.langfuse_enabled:
            env_example = output / ".env.example"
            env_example.write_text(self._get_env_template(), encoding="utf-8")
            if self.verbose:
                typer.echo(f"   生成: {env_example}")

    def _create_instrumented_file(
        self,
        original_path: str,
        output_path: Path,
        entry_point: str,
        force: bool = False,
    ):
        """创建带追踪的版本"""
        source = Path(original_path).read_text(encoding="utf-8")

        if "@trace_skill_execution" not in source:
            tree = ast.parse(source)
            for node in ast.walk(tree):  # type: ignore[attr-defined]
                if isinstance(node, ast.FunctionDef) and node.name == entry_point:
                    import ast as ast_module
                    decorator = ast_module.Name(id="trace_skill_execution")
                    node.decorator_list.insert(0, decorator)

            instrumented_source = ast.unparse(tree)
            output_path.write_text(instrumented_source, encoding="utf-8")
        else:
            if not force:
                typer.echo(f"⚠️ {original_path} 已有追踪装饰器")
            output_path.write_text(source, encoding="utf-8")

    def _get_env_template(self) -> str:
        return """# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
"""


@app.command()
def main(
    path: str = typer.Option(..., "--path", "-p", help="现有 Skill 路径"),
    entry_point: str | None = typer.Option(None, "--entry-point", "-e", help="入口函数名"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="输出目录"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅分析，不修改"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已有文件"),
    langfuse: bool = typer.Option(False, "--langfuse", "-l", help="启用 Langfuse 追踪"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """
    一键观测化现有 Agent Skill

    示例:
        stop observe ./my-existing-skill
        stop observe ./my-existing-skill --langfuse --dry-run
    """
    skill_path = Path(path)
    if not skill_path.exists():
        typer.echo(f"❌ Skill 路径不存在: {path}", err=True)
        raise typer.Exit(1)

    analyzer = SkillCodeAnalyzer()
    observer = SkillObserver(langfuse_enabled=langfuse, verbose=verbose)

    if verbose:
        typer.echo(f"🔍 分析 Skill: {skill_path}")

    try:
        analysis_result = analyzer.analyze(skill_path, entry_point=entry_point)
    except ValueError as e:
        typer.echo(f"❌ 分析失败: {e}", err=True)
        raise typer.Exit(1)

    if verbose:
        typer.echo(f"   发现入口函数: {analysis_result.entry_point}")
        typer.echo(f"   输入参数: {len(analysis_result.inputs)} 个")
        typer.echo(f"   输出参数: {len(analysis_result.outputs)} 个")

    if dry_run:
        typer.echo("\n📝 Dry Run - 以下是建议的修改:")
        typer.echo(analysis_result.to_text())
        return

    observer.instrument(
        skill_path=skill_path,
        analysis=analysis_result,
        output_dir=output_dir,
        force=force,
    )

    typer.echo("\n✅ 观测化完成!")
    typer.echo("   生成文件:")
    typer.echo("   - skill.yaml (Manifest)")
    typer.echo(f"   - {analysis_result.entry_point}_instrumented.py (追踪版本)")
    if langfuse:
        typer.echo("   - .env.example (Langfuse 配置)")


if __name__ == "__main__":
    app()
