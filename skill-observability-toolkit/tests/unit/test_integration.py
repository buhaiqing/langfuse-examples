"""
Integration Tests for Phase 1.

This module tests the integration of all Phase 1 components:
- ManifestParser + AssertionEngine
- Tracer + AssertionEngine
- Full end-to-end workflow
"""

import pytest
import time
from unittest.mock import Mock, patch
from pathlib import Path

from skill_observability_toolkit.stop.manifest import ManifestParser
from skill_observability_toolkit.stop.assertions import AssertionEngine
from skill_observability_toolkit.stop.tracer import STOPTracer, tracer_context


class TestIntegrationManifestAndAssertions:
    """Integration tests for ManifestParser and AssertionEngine."""
    
    def test_full_manifest_and_assertion_workflow(self, tmp_path):
        """Test complete workflow: parse manifest + run assertions."""
        # Create a skill.yaml
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: integration-skill
version: "1.0.0"
description: "Integration test skill"

inputs:
  - name: query
    type: string
    required: true

outputs:
  - name: result
    type: string
    guaranteed: true

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
  post:
    - check: "output_exists"
      field: "result"
      message: "Result must exist"
""")
        
        # Parse manifest
        parser = ManifestParser()
        manifest = parser.load(str(skill_yaml))
        
        assert manifest.name == "integration-skill"
        assert manifest.version == "1.0.0"
        
        # Run pre-assertions
        engine = AssertionEngine()
        pre_assertions = [
            {"check": "string_not_empty", "value": "test query"}
        ]
        pre_results = engine.run_assertions(pre_assertions)
        
        assert len(pre_results) == 1
        assert pre_results[0].passed is True
        
        # Run post-assertions (simulated)
        post_assertions = [
            {"check": "output_exists", "field": "result"}
        ]
        post_results = engine.run_assertions(post_assertions)
        
        assert len(post_results) == 1
        assert post_results[0].passed is True
        
        # Calculate Trust Score
        all_results = pre_results + post_results
        trust_score = engine.calculate_trust_score(all_results)
        
        assert trust_score == 1.0  # All passed


class TestIntegrationTracerAndAssertions:
    """Integration tests for Tracer and AssertionEngine."""
    
    def test_tracer_records_assertion_scores(self):
        """Test that tracer records assertion results as scores."""
        tracer = STOPTracer()
        engine = AssertionEngine()
        
        # Start trace
        tracer.start_trace(name="test_assertion_workflow")
        
        # Run assertions in a span
        assertions = [
            {"check": "value_equal", "value": 5, "expected": 5},
            {"check": "string_not_empty", "value": "hello"},
        ]
        
        with tracer.start_span(name="assertion_execution") as span:
            results = engine.run_assertions(assertions)
            
            # Calculate Trust Score
            trust_score = engine.calculate_trust_score(results)
            
            # Score the span
            span.score("assertions_passed", trust_score, "NUMERIC")
            span.end()
        
        # End trace
        trace_data = tracer.end_trace()
        
        # Verify
        assert len(trace_data["spans"]) == 2  # root + assertion span
        assertion_span = trace_data["spans"][1]
        
        assert "scores" in assertion_span
        assert any(s["name"] == "assertions_passed" for s in assertion_span["scores"])
        
        # Trust Score should be 1.0 (all assertions passed)
        assert trust_score == 1.0
    
    def test_tracer_records_failed_assertions(self):
        """Test that tracer records failed assertions with lower score."""
        tracer = STARTTracer()
        engine = AssertionEngine()
        
        tracer.start_trace(name="failed_assertions_workflow")
        
        # Run assertions (one will fail)
        assertions = [
            {"check": "value_equal", "value": 5, "expected": 5},  # Pass
            {"check": "value_equal", "value": 5, "expected": 10},  # Fail
        ]
        
        with tracer.start_span(name="assertion_execution") as span:
            results = engine.run_assertions(assertions)
            trust_score = engine.calculate_trust_score(results)
            span.score("assertions_passed", trust_score, "NUMERIC")
            span.end()
        
        trace_data = tracer.end_trace()
        
        # Trust Score should be 0.5 (1/2 passed)
        assert trust_score == 0.5
        
        # Verify in trace
        assertion_span = trace_data["spans"][1]
        scores = assertion_span["scores"]
        passed_score = next(s for s in scores if s["name"] == "assertions_passed")
        
        assert passed_score["value"] == 0.5


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_full_e2e_workflow(self):
        """Test complete end-to-end workflow."""
        tracer = STOPTracer()
        engine = AssertionEngine()
        
        # 1. Start trace
        trace_id = tracer.start_trace(name="e2e_test")
        
        # 2. Run pre-assertions
        with tracer.start_span(name="pre_assertions") as span:
            pre_assertions = [
                {"check": "string_not_empty", "value": "test input"},
            ]
            pre_results = engine.run_assertions(pre_assertions)
            pre_score = engine.calculate_trust_score(pre_results)
            span.score("pre_assertions_score", pre_score, "NUMERIC")
            span.end()
        
        # 3. Simulate skill execution
        with tracer.start_span(name="skill_execution") as span:
            time.sleep(0.01)  # Simulate work
            result = {"success": True, "output": "test output"}
            span.end(output=result)
        
        # 4. Run post-assertions
        with tracer.start_span(name="post_assertions") as span:
            post_assertions = [
                {"check": "output_exists", "field": "result"},
                {"check": "value_equal", "value": True, "expected": True},
            ]
            post_results = engine.run_assertions(post_assertions)
            post_score = engine.calculate_trust_score(post_results)
            span.score("post_assertions_score", post_score, "NUMERIC")
            span.end()
        
        # 5. Calculate total Trust Score
        total_results = pre_results + post_results
        total_score = engine.calculate_trust_score(total_results)
        
        # 6. End trace
        trace_data = tracer.end_trace()
        
        # Verify
        assert len(trace_data["spans"]) == 4  # root + 3 operation spans
        assert trace_data["status"] == "success"
        
        # All assertions should pass
        assert total_score == 1.0
        
        # All spans should have scores
        for span in trace_data["spans"][1:]:  # Skip root
            assert "scores" in span
            assert len(span["scores"]) > 0
    
    def test_e2e_workflow_with_failures(self):
        """Test end-to-end workflow with some failures."""
        tracer = STOPTracer()
        engine = AssertionEngine()
        
        tracer.start_trace(name="e2e_with_failures")
        
        # Mix of passing and failing assertions
        assertions = [
            {"check": "value_equal", "value": 5, "expected": 5},  # Pass
            {"check": "string_not_empty", "value": "hello"},  # Pass
            {"check": "value_equal", "value": 5, "expected": 10},  # Fail
            {"check": "type_is", "value": "hello", "expected": "str"},  # Pass
        ]
        
        with tracer.start_span(name="mixed_assertions") as span:
            results = engine.run_assertions(assertions)
            trust_score = engine.calculate_trust_score(results)
            span.score("trust_score", trust_score, "NUMERIC")
            span.end()
        
        trace_data = tracer.end_trace()
        
        # 3/4 passed = 0.75
        assert trust_score == 0.75
    
    def test_tracer_records_timing(self):
        """Test that tracer records timing information."""
        tracer = STOPTracer()
        tracer.start_trace(name="timing_test")
        
        with tracer.start_span(name="slow_operation") as span:
            time.sleep(0.02)  # 20ms
            span.end()
        
        with tracer.start_span(name="fast_operation") as span:
            span.end()
        
        trace_data = tracer.end_trace()
        
        # Check durations
        spans_by_name = {s["name"]: s for s in trace_data["spans"][1:]}
        
        slow_duration = spans_by_name["slow_operation"]["duration_ms"]
        fast_duration = spans_by_name["fast_operation"]["duration_ms"]
        
        # Slow should be > 20ms
        assert slow_duration >= 20
        # Fast should be < 10ms
        assert fast_duration < 10


class TestIntegrationWithExistingTests:
    """Integration with existing test files."""
    
    def test_assertions_engine_with_manifest(self, tmp_path):
        """Test AssertionEngine works with ManifestParser data."""
        # Create skill.yaml with various assertion types
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: full-integration-skill
version: "0.2.0"
description: "Full integration test"

inputs:
  - name: data_file
    type: file_path
    required: true

outputs:
  - name: analysis
    type: json
    guaranteed: true

assertions:
  pre:
    - check: "file_exists"
      value: "${inputs.data_file}"
    - check: "string_not_empty"
      value: "${inputs.data_file}"
  post:
    - check: "output_exists"
      field: "analysis"
    - check: "output_success"
      value: "${outputs.analysis.success}"
""")
        
        # Use manifest
        parser = ManifestParser()
        manifest = parser.load(str(skill_yaml))
        
        # Test with AssertionEngine
        engine = AssertionEngine()
        
        # Pre-assertions
        pre_context = {
            "inputs": {
                "data_file": str(tmp_path / "test.txt")
            }
        }
        
        # We can't test file_exists without creating the file
        # But we can test string_not_empty
        string_results = engine.run_assertions(
            [{"check": "string_not_empty", "value": "test.txt"}]
        )
        assert string_results[0].passed is True
        
        # Post-assertions
        post_context = {
            "outputs": {
                "analysis": {
                    "success": True
                }
            }
        }
        
        # Test value checks
        value_results = engine.run_assertions(
            [{"check": "value_equal", "value": True, "expected": True}]
        )
        assert value_results[0].passed is True
    
    def test_tracer_context_with_assertions(self):
        """Test tracer context works with AssertionEngine."""
        from src.skill_observability_toolkit.stop.tracer import tracer_context
        
        tracer = STOPTracer()
        engine = AssertionEngine()
        
        tracer.start_trace(name="context_test")
        
        # Push a span to context
        span = tracer.start_span(name="context_span")
        
        # Run assertions in that context
        assertions = [
            {"check": "value_greater_than", "value": 10, "expected": 5},
        ]
        
        results = engine.run_assertions(assertions)
        trust_score = engine.calculate_trust_score(results)
        
        # Score should be 1.0
        assert trust_score == 1.0
        
        # Clean up
        span.end()
        tracer.end_trace()


class TestPerformance:
    """Performance tests for integrated components."""
    
    def test_batch_assertions_performance(self):
        """Test performance with batch assertions."""
        engine = AssertionEngine()
        
        # Create many assertions
        assertions = [
            {"check": "value_equal", "value": i, "expected": i}
            for i in range(50)
        ]
        
        start = time.time()
        results = engine.run_assertions(assertions)
        elapsed = time.time() - start
        
        # All should pass
        assert all(r.passed for r in results)
        assert len(results) == 50
        
        # Should complete quickly (< 100ms)
        assert elapsed < 0.1
    
    def test_tracer_batch_performance(self):
        """Test performance with many spans."""
        tracer = STOPTracer()
        tracer.start_trace(name="batch_span_test")
        
        start = time.time()
        
        for i in range(20):
            with tracer.start_span(name=f"span_{i}") as span:
                span.end()
        
        elapsed = time.time() - start
        trace_data = tracer.end_trace()
        
        # Should have 21 spans (1 root + 20 operation)
        assert len(trace_data["spans"]) == 21
        
        # Should complete quickly (< 100ms)
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
