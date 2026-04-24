"""OpenSkills format compatibility for STOP Protocol."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class OpenSkillsCapability:
    """OpenSkills capability definition."""
    type: str
    description: str | None = None


@dataclass
class OpenSkillsInput:
    """OpenSkills input definition."""
    name: str
    type: str
    required: bool = True
    description: str | None = None


@dataclass
class OpenSkillsOutput:
    """OpenSkills output definition."""
    name: str
    type: str
    description: str | None = None


@dataclass
class OpenSkillsManifest:
    """Complete OpenSkills manifest."""
    name: str
    version: str
    description: str
    capabilities: list[OpenSkillsCapability] = field(default_factory=list)
    inputs: list[OpenSkillsInput] = field(default_factory=list)
    outputs: list[OpenSkillsOutput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": [
                {"type": c.type, "description": c.description}
                for c in self.capabilities
            ],
            "inputs": [
                {
                    "name": i.name,
                    "type": i.type,
                    "required": i.required,
                    "description": i.description,
                }
                for i in self.inputs
            ],
            "outputs": [
                {
                    "name": o.name,
                    "type": o.type,
                    "description": o.description,
                }
                for o in self.outputs
            ],
            "metadata": self.metadata,
        }


class OpenSkillsImporter:
    """Import OpenSkills format to STOP skill.yaml."""

    TYPE_MAP = {
        "string": "string",
        "str": "string",
        "integer": "integer",
        "int": "integer",
        "number": "number",
        "float": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "array": "array",
        "list": "array",
        "object": "json",
        "dict": "json",
    }

    def __init__(self):
        pass

    def import_file(self, path: str | Path) -> dict[str, Any]:
        """
        Import OpenSkills YAML file and convert to STOP skill.yaml format.

        Args:
            path: Path to OpenSkills YAML file

        Returns:
            STOP skill.yaml compatible dictionary
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"OpenSkills file not found: {path}")

        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self.convert(data)

    def convert(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert OpenSkills format to STOP skill.yaml format.

        Args:
            data: OpenSkills dictionary

        Returns:
            STOP skill.yaml compatible dictionary
        """
        inputs = []
        for inp in data.get("inputs", []):
            inp_type = self.TYPE_MAP.get(inp.get("type", "string").lower(), "string")
            inputs.append({
                "name": inp.get("name", "input"),
                "type": inp_type,
                "required": inp.get("required", True),
                "description": inp.get("description", ""),
            })

        outputs = []
        for out in data.get("outputs", []):
            out_type = self.TYPE_MAP.get(out.get("type", "string").lower(), "string")
            outputs.append({
                "name": out.get("name", "result"),
                "type": out_type,
                "description": out.get("description", ""),
                "guaranteed": True,
            })

        capabilities = data.get("capabilities", [])
        tools_used = self._capabilities_to_tools(capabilities)

        return {
            "sop": "1.0.0",
            "name": self._to_kebab_case(data.get("name", "unknown-skill")),
            "version": data.get("version", "0.1.0"),
            "description": data.get("description", ""),
            "inputs": inputs,
            "outputs": outputs,
            "tools_used": tools_used,
            "observability": {
                "level": "L2",
                "langfuse_integration": True,
                "capabilities": capabilities,
            },
        }

    def _capabilities_to_tools(self, capabilities: list[dict[str, Any]]) -> list[str]:
        """Map capabilities to tools_used."""
        tool_mapping = {
            "text-processing": ["text_processing"],
            "code-execution": ["code_execution"],
            "web-search": ["web_search"],
            "file-read": ["read_file"],
            "file-write": ["write_file"],
            "api-integration": ["http_request"],
            "database": ["database_query"],
        }

        tools = []
        for cap in capabilities:
            cap_type = cap.get("type", "").lower()
            if cap_type in tool_mapping:
                tools.extend(tool_mapping[cap_type])

        return list(set(tools)) if tools else ["unknown"]

    def _to_kebab_case(self, name: str) -> str:
        """Convert name to kebab-case."""
        import re
        name = re.sub(r"([A-Z])", r"-\1", name)
        name = re.sub(r"[\s_]+", "-", name)
        return name.strip("-").lower()


class OpenSkillsExporter:
    """Export STOP skill.yaml to OpenSkills format."""

    REVERSE_TYPE_MAP = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "json": "object",
        "file_path": "string",
    }

    def __init__(self):
        pass

    def export_file(self, skill_yaml: str | Path, output: str | Path) -> None:
        """
        Export STOP skill.yaml to OpenSkills YAML file.

        Args:
            skill_yaml: Path to skill.yaml
            output: Output path for OpenSkills YAML
        """
        path = Path(skill_yaml)
        if not path.exists():
            raise FileNotFoundError(f"skill.yaml not found: {path}")

        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        openskills = self.convert(data)

        output_path = Path(output)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(openskills.to_dict(), f, default_flow_style=False, allow_unicode=True)

    def convert(self, data: dict[str, Any]) -> OpenSkillsManifest:
        """
        Convert STOP skill.yaml to OpenSkills format.

        Args:
            data: STOP skill.yaml dictionary

        Returns:
            OpenSkillsManifest object
        """
        inputs = []
        for inp in data.get("inputs", []):
            inp_type = self.REVERSE_TYPE_MAP.get(inp.get("type", "string"), "string")
            inputs.append(OpenSkillsInput(
                name=inp.get("name", "input"),
                type=inp_type,
                required=inp.get("required", True),
                description=inp.get("description"),
            ))

        outputs = []
        for out in data.get("outputs", []):
            out_type = self.REVERSE_TYPE_MAP.get(out.get("type", "string"), "string")
            outputs.append(OpenSkillsOutput(
                name=out.get("name", "result"),
                type=out_type,
                description=out.get("description"),
            ))

        observability = data.get("observability", {})
        capabilities = []
        for cap in observability.get("capabilities", []):
            if isinstance(cap, str):
                capabilities.append(OpenSkillsCapability(type=cap))
            elif isinstance(cap, dict):
                capabilities.append(OpenSkillsCapability(
                    type=cap.get("type", "unknown"),
                    description=cap.get("description"),
                ))

        return OpenSkillsManifest(
            name=data.get("name", "unknown-skill"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            capabilities=capabilities,
            inputs=inputs,
            outputs=outputs,
            metadata=data.get("metadata", {}),
        )
