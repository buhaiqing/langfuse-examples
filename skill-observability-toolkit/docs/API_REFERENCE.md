# API Reference

> **Version**: 0.1.0

> **Python**: 3.10+
## STOP Protocol API

### ManifestParser

Parse and validate skill.yaml files.

```python
from skill_observability_toolkit.stop.manifest import ManifestParser
parser = ManifestParser(skill_yaml_path="skill.yaml" )
manifest = parser.parse()
```

### STOPTracer

Record execution traces.

from skill_observability_toolkit.stop.tracer import STOPTracer
```python
tracer = STOPTracer(output_path="trace.ndjson" )
tracer.start_trace(name="skill:my_skill" )
tracer.end_trace()
```
