# Basic Tracing Skill Example

This example demonstrates the STOP Protocol with tracing implementation.

## Overview

This skill shows how to:
1. Parse a `skill.yaml` manifest using the STOP Protocol
2. Validate inputs with pre-execution assertions
3. Execute the skill logic
4. Validate outputs with post-execution assertions
5. Calculate Trust Score based on assertion results
6. Record execution trace in NDJSON format

## Quick Start

### 1. Create a test input file

```bash
cd examples/basic-skill

# Create a sample text file
echo "Hello World! This is a test file for the basic tracing skill.
It contains multiple lines of text.
We can count words, analyze structure, or transform the content." > data.txt
```

### 2. Run the skill

```bash
# Using Python directly
python src/main.py

# Or with arguments
python src/main.py --input-file data.txt --process-type count

# Available process types:
#   count    - Count words and characters
#   analyze  - Analyze text structure
#   transform - Transform content format
```

### 3. View the trace output

The skill saves execution trace to `trace.ndjson`:

```bash
cat trace.ndjson
```

Expected output:
```json
{
  "trace_id": "example_trace_001",
  "skill_name": "basic-tracing-skill",
  "skill_version": "1.0.0",
  "inputs": {
    "input_file": "data.txt",
    "process_type": "count"
  },
  "result": {
    "success": true,
    "stats": {
      "word_count": 20,
      "char_count": 150,
      "duration_ms": 5
    }
  },
  "trust_score": 1.0,
  "assertions": {
    "pre": 3,
    "post": 4
  }
}
```

## Project Structure

```
examples/basic-skill/
├── skill.yaml          # Skill manifest (STOP Protocol L0)
├── src/
│   └── main.py         # Main execution script
├── data.txt           # Sample input file (create this)
├── trace.ndjson       # Execution trace (generated)
└── README.md          # This file
```

## Skill Manifest

The `skill.yaml` defines:

### Inputs
- `input_file`: Path to input file (required)
- `process_type`: Processing type - "count", "analyze", or "transform"

### Outputs
- `result`: Processing result with success status and statistics

### Assertions
**Pre-execution (4 checks):**
- File exists
- Input file path not empty
- Process type is valid

**Post-execution (4 checks):**
- Result exists
- Processing succeeded
- Word count provided
- Performance within time limit

### Trust Score
- Enabled: true
- History window: 30 days
- Minimum pass rate: 80%

## Usage Examples

### Example 1: Count Words

```bash
python src/main.py --input-file data.txt --process-type count
```

Output:
```
🚀 Starting Basic Tracing Skill
============================================================
📄 Loading manifest from: skill.yaml
✨ Manifest parsed successfully!
   Skill: basic-tracing-skill v1.0.0
   Inputs: 2
   Outputs: 1
   Assertions: 7

🔍 Running pre-execution assertions...
   Checking: file_exists...
   ✓ file_exists: PASSED
   Checking: string_not_empty...
   ✓ string_not_empty: PASSED
   Checking: input_valid...
   ✓ input_valid: PASSED

⚙️  Processing content...
   Counting words and characters...
   Words: 20
   Chars: 150

🔍 Running post-execution assertions...
   Checking: output.exists...
   ✓ output.exists: PASSED
   Checking: output.success...
   ✓ output.success: PASSED
   Checking: output.not_empty...
   ✓ output.not_empty: PASSED
   Checking: performance...
   ✓ performance: PASSED

📊 Trust Score Calculation:
   Passed: 7
   Total: 7
   Score: 1.00 (0.0 - 1.0)

============================================================
📄 TRACE SUMMARY
============================================================

Skill Information:
   Name: basic-tracing-skill
   Version: 1.0.0

Inputs:
   input_file: data.txt
   process_type: count

Results:
   ✓ Success: True
   Word Count: 20
   Char Count: 150
   Duration: 5 ms

Trust Score: 1.00
============================================================

✨ Execution completed successfully!
   Trust Score: 1.00
```

### Example 2: Analyze Text

```bash
python src/main.py --input-file data.txt --process-type analyze
```

### Example 3: Transform Content

```bash
python src/main.py --input-file data.txt --process-type transform
```

## Integration with STOP Protocol

This example uses the STOP Protocol through the `ManifestParser`:

```python
from skill_observability_toolkit.stop.manifest import ManifestParser

# Parse the manifest
parser = ManifestParser(skill_yaml_path="skill.yaml")
manifest = parser.parse()

# Run pre-execution assertions
pre_results = run_assertions(parser, manifest, inputs)

# Execute the skill
result = process_content(...)

# Run post-execution assertions
post_results = run_post_assertions(parser, manifest, result)

# Calculate Trust Score
trust_score = parser.add_trust_score(pre_results + post_results)
```

## Next Steps

This is a simple example. To extend it:

1. **Add real tools**: Replace simulated tools with actual implementations
2. **Integrate with Langfuse**: Use the `LangfuseClient` to send traces
3. **Add more assertions**: Implement custom assertion types
4. **Persist Trust Score**: Store historical assertion results

See upcoming tasks:
- Task 1.3: Implement STOP Tracer with NDJSON output
- Task 1.5: Integrate with Langfuse SDK
- Task 1.6: Add tracing decorators

## Requirements

- Python 3.10+
- PyYAML
- (Future) Langfuse SDK (Task 1.5)

## License

MIT