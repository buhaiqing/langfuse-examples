"""
Tests for Tracing Decorators.

This module tests the tracing decorators for skills and tools.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from skill_observability_toolkit.langfuse_integration.decorators import (
    trace_skill_execution,
    trace_tool_call,
    trace_function,
)


class TestTraceSkillExecution:
    """Tests for trace_skill_execution decorator."""
    
    def test_decorator_returns_wrapped_function(self):
        """Test decorator returns the wrapped function."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            return x * 2
        
        assert callable(test_skill)
        assert test_skill.__name__ == "test_skill"
    
    def test_decorator_executes_function(self):
        """Test decorator executes the wrapped function."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            return x * 2
        
        result = test_skill(5)
        assert result == 10
    
    def test_decorator_creates_span(self):
        """Test decorator creates a span."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            return x * 2
        
        with patch("src.skill_observability_toolkit.langfuse_integration.decorators.STOPTracer") as mock_tracer_cls:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_tracer.start_span.return_value = mock_span
            mock_tracer.end_trace = Mock()
            mock_tracer_cls.return_value = mock_tracer
            
            with patch("src.skill_observability_toolkit.langfuse_integration.decorators.get_trace_id", return_value=None):
                result = test_skill(5)
                
                assert result == 10
                mock_tracer.start_span.assert_called_once()
                mock_span.end.assert_called_once()
    
    def test_decorator_scores_trace_success(self):
        """Test decorator scores trace on success."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            return x * 2
        
        with patch("src.skill_observability_toolkit.langfuse_integration.decorators.LangfuseClient") as mock_client_cls:
            mock_client = Mock()
            mock_client.score_trace = Mock()
            mock_client.get_instance.return_value = mock_client
            mock_client_cls.get_instance.return_value = mock_client
            
            with patch("src.skill_observability_toolkit.langfuse_integration.decorators.STOPTracer"):
                with patch("src.skill_observability_toolkit.langfuse_integration.decorators.get_trace_id", return_value=None):
                    result = test_skill(5)
                    
                    assert result == 10
                    # Should score success and timing
                    assert mock_client.score_trace.call_count >= 1
    
    def test_decorator_handles_error(self):
        """Test decorator handles exceptions."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            if x > 10:
                raise ValueError("Too large!")
            return x * 2
        
        with pytest.raises(ValueError):
            test_skill(15)
    
    def test_decorator_executes_within_timeout(self):
        """Test decorator executes within reasonable time."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def test_skill(x: int) -> int:
            time.sleep(0.01)
            return x * 2
        
        start = time.time()
        result = test_skill(5)
        elapsed = time.time() - start
        
        assert result == 10
        assert elapsed < 1.0  # Should complete within 1 second


class TestTraceToolCall:
    """Tests for trace_tool_call decorator."""
    
    def test_decorator_returns_wrapped_function(self):
        """Test decorator returns the wrapped function."""
        @trace_tool_call(tool_name="test_tool")
        def test_tool(x: int) -> int:
            return x * 2
        
        assert callable(test_tool)
        assert test_tool.__name__ == "test_tool"
    
    def test_decorator_executes_function(self):
        """Test decorator executes the wrapped function."""
        @trace_tool_call(tool_name="test_tool")
        def test_tool(x: int) -> int:
            return x * 2
        
        result = test_tool(5)
        assert result == 10
    
    def test_decorator_creates_span(self):
        """Test decorator creates a span."""
        @trace_tool_call(tool_name="test_tool")
        def test_tool(x: int) -> int:
            return x * 2
        
        with patch("src.skill_observability_toolkit.langfuse_integration.decorators.STOPTracer") as mock_tracer_cls:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_tracer.start_span.return_value = mock_span
            mock_tracer.end_trace = Mock()
            mock_tracer_cls.return_value = mock_tracer
            
            with patch("src.skill_observability_toolkit.langfuse_integration.decorators.get_trace_id", return_value=None):
                result = test_tool(5)
                
                assert result == 10
                mock_tracer.start_span.assert_called_once()
    
    def test_decorator_scores_trace_success(self):
        """Test decorator scores trace on success."""
        @trace_tool_call(tool_name="test_tool")
        def test_tool(x: int) -> int:
            return x * 2
        
        with patch("src.skill_observability_toolkit.langfuse_integration.decorators.LangfuseClient") as mock_client_cls:
            mock_client = Mock()
            mock_client.score_trace = Mock()
            mock_client.get_instance.return_value = mock_client
            mock_client_cls.get_instance.return_value = mock_client
            
            with patch("src.skill_observability_toolkit.langfuse_integration.decorators.STOPTracer"):
                with patch("src.skill_observability_toolkit.langfuse_integration.decorators.get_trace_id", return_value=None):
                    result = test_tool(5)
                    
                    assert result == 10
                    assert mock_client.score_trace.call_count >= 1


class TestTraceFunction:
    """Tests for generic trace_function decorator."""
    
    def test_decorator_returns_wrapped_function(self):
        """Test decorator returns the wrapped function."""
        @trace_function(name="test_function")
        def test_func(x: int) -> int:
            return x * 2
        
        assert callable(test_func)
        assert test_func.__name__ == "test_func"
    
    def test_decorator_executes_function(self):
        """Test decorator executes the wrapped function."""
        @trace_function(name="test_function")
        def test_func(x: int) -> int:
            return x * 2
        
        result = test_func(5)
        assert result == 10
    
    def test_decorator_creates_span(self):
        """Test decorator creates a span."""
        @trace_function(name="test_function")
        def test_func(x: int) -> int:
            return x * 2
        
        with patch("src.skill_observability_toolkit.langfuse_integration.decorators.STOPTracer") as mock_tracer_cls:
            mock_tracer = Mock()
            mock_span = Mock()
            mock_tracer.start_span.return_value = mock_span
            mock_tracer.end_trace = Mock()
            mock_tracer_cls.return_value = mock_tracer
            
            with patch("src.skill_observability_toolkit.langfuse_integration.decorators.get_trace_id", return_value=None):
                result = test_func(5)
                
                assert result == 10
                mock_tracer.start_span.assert_called_once()
                assert "test_function" in mock_tracer.start_span.call_args[1]["name"]


class TestIntegration:
    """Integration tests for decorators."""
    
    def test_nested_decorators(self):
        """Test using multiple decorators together."""
        @trace_tool_call(tool_name="helper_tool")
        def helper(x: int) -> int:
            return x * 2
        
        @trace_skill_execution(skill_name="main-skill", version="1.0.0")
        def main_skill(x: int) -> int:
            return helper(x) + 1
        
        # Decorators should work together
        result = main_skill(5)
        assert result == 11  # (5 * 2) + 1
    
    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve function metadata."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def documented_skill(x: int) -> int:
            """This is a documented skill."""
            return x * 2
        
        assert documented_skill.__doc__ == "This is a documented skill."
        assert documented_skill.__name__ == "documented_skill"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
