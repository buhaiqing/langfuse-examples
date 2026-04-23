"""
STOP Protocol Manifest module for parsing skill.yaml files.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml


class ManifestError(Exception):
    """Base class for manifest-related errors."""
    pass


class ManifestParseError(ManifestError):
    """Error parsing the manifest file."""
    pass


class ManifestValidationError(ManifestError):
    """Error validating the manifest structure."""
    pass


@dataclass
class SkillInput:
    """
    Skill input parameter definition.
    
    Attributes:
        name: Input parameter name
        type: Data type (string, integer, boolean, object, array)
        description: Human-readable description
        required: Whether this input is required (default: True)
        default: Default value if not provided
    """
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
        }


@dataclass
class SkillOutput:
    """
    Skill output definition.
    
    Attributes:
        name: Output parameter name
        type: Data type
        description: Human-readable description
        properties: For object type, define property schema
    """
    name: str
    type: str
    description: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "properties": self.properties,
        }


@dataclass
class ToolReference:
    """
    Reference to an external tool used by the Skill.
    
    Attributes:
        name: Tool name
        version: Tool version
        description: Tool description
    """
    name: str
    version: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }


@dataclass
class Assertion:
    """
    Assertion for validation (pre-check or post-check).
    
    Attributes:
        check: Check type (e.g., "file_exists", "output.exists")
        path: Path to the value being checked (optional)
        condition: Python expression for custom validation (optional)
        message: Human-readable error message
        type: Assertion type ("pre" or "post")
    """
    check: str
    path: Optional[str] = None
    condition: Optional[str] = None
    message: str = ""
    type: str = "pre"  # "pre" or "post"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"check": self.check, "message": self.message, "type": self.type}
        if self.path is not None:
            result["path"] = self.path
        if self.condition is not None:
            result["condition"] = self.condition
        return result


@dataclass
class TrustScoreConfig:
    """
    Trust Score configuration.
    
    Attributes:
        enabled: Whether Trust Score tracking is enabled (default: True)
        history_window: Number of days to keep history (default: 30)
        min_pass_rate: Minimum pass rate for trust score (default: 0.8)
    """
    enabled: bool = True
    history_window: int = 30  # days
    min_pass_rate: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "history_window": self.history_window,
            "min_pass_rate": self.min_pass_rate,
        }


@dataclass
class SkillManifest:
    """
    Parsed Skill Manifest.
    
    Attributes:
        name: Skill name
        version: Skill version
        description: Skill description
        tags: List of tags for categorization
        sop: Standard Operating Procedure (text or reference)
        sop_source: "inline" or "file"
        inputs: List of input parameters
        outputs: List of output definitions
        tools_used: List of referenced tools
        assertions: List of assertion rules
        trust_score: Trust Score configuration
        metadata: Additional metadata
    """
    name: str
    version: str
    description: str
    tags: List[str] = field(default_factory=list)
    
    sop: str = ""
    sop_source: str = "inline"
    
    inputs: List[SkillInput] = field(default_factory=list)
    outputs: List[SkillOutput] = field(default_factory=list)
    tools_used: List[ToolReference] = field(default_factory=list)
    
    assertions: List[Assertion] = field(default_factory=list)
    
    trust_score: TrustScoreConfig = field(default_factory=TrustScoreConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "sop": self.sop,
            "sop_source": self.sop_source,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "tools_used": [t.to_dict() for t in self.tools_used],
            "assertions": [a.to_dict() for a in self.assertions],
            "trust_score": self.trust_score.to_dict(),
            "metadata": self.metadata,
        }


class ManifestParser:
    """
    Parser for STOP Protocol Manifest files.
    
    Reads and validates skill.yaml files, parsing them into
    SkillManifest dataclasses with full type checking.
    
    Attributes:
        skill_yaml_path: Path to the skill.yaml file (optional)
        manifest: Parsed SkillManifest (set after parse())
        errors: List of parsing/validation errors
        warnings: List of warnings
    """
    
    REQUIRED_FIELDS = ["name", "version", "sop"]
    
    def __init__(self, skill_yaml_path: Optional[str] = None):
        """
        Initialize the manifest parser.
        
        Args:
            skill_yaml_path: Optional path to skill.yaml file.
                            If provided, will automatically parse on parse().
        """
        self.skill_yaml_path: Optional[str] = skill_yaml_path
        self.manifest: Optional[SkillManifest] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse(self, content: Optional[str] = None) -> SkillManifest:
        """
        Parse the skill manifest from content or file.
        
        Args:
            content: Optional YAML content string. If None, reads from skill_yaml_path.
            
        Returns:
            Parsed SkillManifest object
            
        Raises:
            ManifestParseError: If parsing fails (invalid YAML, missing required fields)
            ManifestValidationError: If validation fails
        """
        # Read content if not provided
        if content is None:
            if self.skill_yaml_path is None:
                raise ManifestParseError(
                    "No content or skill_yaml_path provided"
                )
            
            content = self._read_file(self.skill_yaml_path)
        
        # Parse YAML
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ManifestParseError(f"Failed to parse YAML: {e}")
        
        # Validate data is a dict
        if not isinstance(data, dict):
            raise ManifestParseError(
                f"Manifest must be a YAML object (dict), got {type(data).__name__}"
            )
        
        # Check required fields
        self._validate_required_fields(data)
        
        # Build SkillManifest
        self.manifest = self._build_manifest(data)
        
        # Validate structure
        validation_errors = self.validate(self.manifest)
        if validation_errors:
            raise ManifestValidationError(
                f"Manifest validation failed:\n{chr(10).join(validation_errors)}"
            )
        
        return self.manifest
    
    def _read_file(self, path: str) -> str:
        """
        Read file content.
        
        Args:
            path: Path to file
            
        Returns:
            File content as string
            
        Raises:
            ManifestParseError: If file cannot be read
        """
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise ManifestParseError(f"Failed to read file '{path}': {e}")
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """
        Validate that all required fields are present.
        
        Args:
            data: Parsed YAML data
            
        Raises:
            ManifestParseError: If required fields are missing
        """
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                missing.append(field)
        
        if missing:
            raise ManifestParseError(
                f"Missing required fields: {', '.join(missing)}"
            )
    
    def _build_manifest(self, data: Dict[str, Any]) -> SkillManifest:
        """
        Build SkillManifest from parsed YAML data.
        
        Args:
            data: Parsed YAML data
            
        Returns:
            SkillManifest object
        """
        # Extract basic fields
        name = str(data["name"]).strip()
        version = str(data["version"]).strip()
        description = str(data.get("description", "")).strip()
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags]
        
        # Extract SOP
        sop = str(data["sop"])
        sop_source = "inline"
        if sop.startswith("file:"):
            sop_source = "file"
            sop = sop[5:].strip()
        
        # Parse inputs
        inputs = []
        for inp in data.get("inputs", []):
            if isinstance(inp, dict):
                inputs.append(
                    SkillInput(
                        name=str(inp["name"]),
                        type=str(inp.get("type", "string")),
                        description=str(inp.get("description", "")),
                        required=inp.get("required", True),
                        default=inp.get("default"),
                    )
                )
        
        # Parse outputs
        outputs = []
        for out in data.get("outputs", []):
            if isinstance(out, dict):
                outputs.append(
                    SkillOutput(
                        name=str(out["name"]),
                        type=str(out.get("type", "object")),
                        description=str(out.get("description", "")),
                        properties=out.get("properties", {}),
                    )
                )
        
        # Parse tools_used
        tools_used = []
        for tool in data.get("tools_used", []):
            if isinstance(tool, dict):
                tools_used.append(
                    ToolReference(
                        name=str(tool["name"]),
                        version=str(tool.get("version", "1.0")),
                        description=str(tool.get("description", "")),
                    )
                )
        
        # Parse assertions
        assertions = []
        for assertion_type in ["pre", "post"]:
            for assertion in data.get("assertions", {}).get(assertion_type, []):
                if isinstance(assertion, dict):
                    assertions.append(
                        Assertion(
                            check=str(assertion["check"]),
                            path=assertion.get("path"),
                            condition=assertion.get("condition"),
                            message=str(assertion.get("message", "")),
                            type=assertion_type,
                        )
                    )
        
        # Parse trust_score
        trust_score_data = data.get("trust_score", {})
        trust_score = TrustScoreConfig(
            enabled=trust_score_data.get("enabled", True),
            history_window=int(trust_score_data.get("history_window", 30)),
            min_pass_rate=float(trust_score_data.get("min_pass_rate", 0.8)),
        )
        
        # Extract metadata
        metadata = {k: v for k, v in data.items() if k not in [
            "name", "version", "description", "tags", "sop", 
            "inputs", "outputs", "tools_used", "assertions", "trust_score"
        ]}
        
        return SkillManifest(
            name=name,
            version=version,
            description=description,
            tags=tags,
            sop=sop,
            sop_source=sop_source,
            inputs=inputs,
            outputs=outputs,
            tools_used=tools_used,
            assertions=assertions,
            trust_score=trust_score,
            metadata=metadata,
        )
    
    def validate(self, manifest: SkillManifest) -> List[str]:
        """
        Validate the parsed manifest structure.
        
        Args:
            manifest: The SkillManifest to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate name
        if not manifest.name or not manifest.name.strip():
            errors.append("Skill name cannot be empty")
        
        # Validate version
        if not manifest.version or not manifest.version.strip():
            errors.append("Skill version cannot be empty")
        
        # Validate inputsHave unique names
        input_names = [inp.name for inp in manifest.inputs]
        if len(input_names) != len(set(input_names)):
            errors.append("Input parameter names must be unique")
        
        # Validate outputs have unique names
        output_names = [out.name for out in manifest.outputs]
        if len(output_names) != len(set(output_names)):
            errors.append("Output parameter names must be unique")
        
        # Validate tools have unique names
        tool_names = [tool.name for tool in manifest.tools_used]
        if len(tool_names) != len(set(tool_names)):
            errors.append("Tool names must be unique")
        
        # Validate assertions
        for assertion in manifest.assertions:
            if not assertion.check:
                errors.append("Assertion 'check' field is required")
            if not assertion.message:
                errors.append("Assertion 'message' field is required")
            if assertion.type not in ["pre", "post"]:
                errors.append(f"Assertion type must be 'pre' or 'post', got '{assertion.type}'")
            
            # Validate check type
            valid_checks = [
                "file_exists", "file_not_empty", "output.exists", 
                "output.success", "output.not_empty", "performance"
            ]
            if not any(assertion.check.startswith(vc) for vc in valid_checks):
                self.warnings.append(
                    f"Unknown assertion check type: {assertion.check}"
                )
        
        return errors
    
    def add_trust_score(self, assertion_results: List[Dict[str, Any]]) -> float:
        """
        Calculate Trust Score based on assertion results.
        
        Trust Score = (Number of passed assertions) / (Total assertions)
        
        Args:
            assertion_results: List of assertion results with 'passed' field
            
        Returns:
            Trust Score (0.0 - 1.0)
        """
        if not assertion_results:
            return 1.0  # No assertions means perfect trust
        
        passed = sum(1 for r in assertion_results if r.get("passed", False))
        total = len(assertion_results)
        
        return passed / total
    
    def get_assertion_results(self, trace_path: str) -> List[Dict[str, Any]]:
        """
        Retrieve assertion results from trace file.
        
        Args:
            trace_path: Path to the NDJSON trace file
            
        Returns:
            List of assertion results with 'check', 'passed', 'message' fields
        """
        results = []
        
        # TODO: Implement actual trace file parsing when T1.3 is complete
        # For now, return empty list
        self.warnings.append(
            "Assertion result retrieval from traces not yet implemented "
            "(requires Task 1.3: STOP Tracer)"
        )
        
        return results
