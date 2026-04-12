"""
Tests for tracing decorators and context management.

This module tests the core tracing functionality including:
- trace_customer_service decorator behavior
- Session ID and user ID binding
- Tag and metadata attachment
- Span creation and management
- Event logging
"""

from unittest.mock import Mock, patch

import pytest

from core.tracing import (
    add_event,
    create_span,
    score_span,
    score_trace,
    trace_customer_service,
    update_trace_metadata,
    update_trace_tags,
)


class TestTraceCustomerServiceDecorator:
    """Test suite for trace_customer_service decorator."""

    @pytest.mark.asyncio
    async def test_decorator_creates_trace_with_basic_config(self):
        """Arrange-Act-Assert: Verify decorator creates trace with correct name and type."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(
            name="test_conversation", session_id="session_123", user_id="user_456"
        )
        async def dummy_handler(query: str):
            return {"result": "success"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await dummy_handler("test query")

        # Assert
        assert result == {"result": "success"}
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert "session_id" in call_kwargs
        assert call_kwargs["session_id"] == "session_123"
        assert "user_id" in call_kwargs

    @pytest.mark.asyncio
    async def test_decorator_binds_session_id_correctly(self):
        """Arrange-Act-Assert: Verify session_id is correctly bound to trace."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(name="api_support", session_id="unique_session_abc")
        async def api_handler(request_data: dict):
            return {"status": "ok"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            await api_handler({"query": "help"})

        # Assert
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["session_id"] == "unique_session_abc"

    @pytest.mark.asyncio
    async def test_decorator_hashes_user_id_for_privacy(self):
        """Arrange-Act-Assert: Verify user_id is hashed before being set."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(name="user_interaction", user_id="sensitive_user_12345")
        async def user_handler(message: str):
            return {"response": "handled"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            await user_handler("Hello")

        # Assert
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert "user_id" in call_kwargs
        # User ID should be hashed (16 character hex string)
        user_id_hash = call_kwargs["user_id"]
        assert len(user_id_hash) == 16
        assert all(c in "0123456789abcdef" for c in user_id_hash)
        # Should not contain original user ID
        assert "sensitive_user_12345" not in user_id_hash

    @pytest.mark.asyncio
    async def test_decorator_attaches_tags_to_trace(self):
        """Arrange-Act-Assert: Verify tags are correctly attached to trace."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        expected_tags = ["technical_support", "api_issue", "high_priority"]

        @trace_customer_service(name="tagged_conversation", tags=expected_tags)
        async def tagged_handler(query: str):
            return {"answer": "resolved"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            await tagged_handler("API error")

        # Assert
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert "tags" in call_kwargs
        assert call_kwargs["tags"] == expected_tags

    @pytest.mark.asyncio
    async def test_decorator_attaches_metadata_to_trace(self):
        """Arrange-Act-Assert: Verify metadata is correctly attached to trace."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        expected_metadata = {"channel": "web_chat", "priority": "high", "category": "billing"}

        @trace_customer_service(name="metadata_test", metadata=expected_metadata)
        async def metadata_handler(request: str):
            return {"result": "done"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            await metadata_handler("Billing question")

        # Assert
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert "metadata" in call_kwargs
        assert call_kwargs["metadata"] == expected_metadata

    @pytest.mark.asyncio
    async def test_decorator_handles_all_parameters_together(self):
        """Arrange-Act-Assert: Verify all parameters work together correctly."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(
            name="comprehensive_test",
            session_id="sess_789",
            user_id="usr_101",
            tags=["multi_param"],
            metadata={"test": "value"},
        )
        async def comprehensive_handler(data: dict):
            return data

        input_data = {"key": "value"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await comprehensive_handler(input_data)

        # Assert
        assert result == input_data
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["session_id"] == "sess_789"
        assert "user_id" in call_kwargs
        assert call_kwargs["tags"] == ["multi_param"]
        assert call_kwargs["metadata"] == {"test": "value"}

    @pytest.mark.asyncio
    async def test_decorator_works_without_optional_parameters(self):
        """Arrange-Act-Assert: Verify decorator works with only required name parameter."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(name="minimal_test")
        async def minimal_handler():
            return "minimal_result"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await minimal_handler()

        # Assert
        assert result == "minimal_result"
        # update_current_trace should not be called when no optional params
        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_signature(self):
        """Arrange-Act-Assert: Verify decorated function preserves original signature."""

        # Arrange
        @trace_customer_service(name="signature_test")
        async def typed_handler(param1: str, param2: int = 10) -> dict:
            return {"param1": param1, "param2": param2}

        # Act
        with patch("core.tracing.langfuse", Mock()):
            result = await typed_handler("test", param2=20)

        # Assert
        assert result == {"param1": "test", "param2": 20}

    @pytest.mark.asyncio
    async def test_decorator_handles_exceptions_gracefully(self):
        """Arrange-Act-Assert: Verify decorator handles exceptions in wrapped function."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(name="error_test", session_id="err_session")
        async def failing_handler():
            raise ValueError("Test error")

        # Act & Assert
        with patch("core.tracing.langfuse", mock_langfuse):
            with pytest.raises(ValueError, match="Test error"):
                await failing_handler()

        # Update should still be called before exception
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_with_empty_session_id(self):
        """Arrange-Act-Assert: Verify empty session_id is handled correctly."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(name="empty_session_test", session_id="")
        async def handler():
            return "ok"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await handler()

        # Assert
        assert result == "ok"
        # Empty string is falsy, so update should not be called
        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_with_none_values(self):
        """Arrange-Act-Assert: Verify None values don't trigger updates."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        @trace_customer_service(
            name="none_test", session_id=None, user_id=None, tags=None, metadata=None
        )
        async def handler():
            return "ok"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await handler()

        # Assert
        assert result == "ok"
        mock_update.assert_not_called()


class TestCreateSpan:
    """Test suite for create_span context manager."""

    def test_create_span_with_basic_params(self):
        """Arrange-Act-Assert: Verify span is created with correct parameters."""
        # Arrange
        mock_langfuse = Mock()
        mock_span = Mock()
        mock_langfuse.start_span.return_value = mock_span

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            span = create_span(
                name="test_span", input_data={"query": "test"}, metadata={"source": "unit_test"}
            )

        # Assert
        mock_langfuse.start_span.assert_called_once()
        call_kwargs = mock_langfuse.start_span.call_args[1]
        assert call_kwargs["name"] == "test_span"
        assert call_kwargs["input"] == {"query": "test"}
        assert call_kwargs["metadata"] == {"source": "unit_test"}
        assert span == mock_span

    def test_create_span_with_none_input(self):
        """Arrange-Act-Assert: Verify span creation works without input_data."""
        # Arrange
        mock_langfuse = Mock()
        mock_span = Mock()
        mock_langfuse.start_span.return_value = mock_span

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            span = create_span(name="minimal_span")

        # Assert
        mock_langfuse.start_span.assert_called_once()
        call_kwargs = mock_langfuse.start_span.call_args[1]
        assert call_kwargs["name"] == "minimal_span"
        assert call_kwargs["input"] is None
        assert call_kwargs["metadata"] is None

    def test_create_span_returns_span_object(self):
        """Arrange-Act-Assert: Verify create_span returns the span object."""
        # Arrange
        mock_langfuse = Mock()
        mock_span = Mock()
        mock_langfuse.start_span.return_value = mock_span

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = create_span(name="return_test")

        # Assert
        assert result is mock_span


class TestScoreTrace:
    """Test suite for score_trace function."""

    def test_score_trace_numeric_type(self):
        """Arrange-Act-Assert: Verify numeric score is recorded correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="test_score", value=0.85, data_type="NUMERIC", comment="Test comment")

        # Assert
        mock_langfuse.score_current_trace.assert_called_once()
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == "test_score"
        assert call_kwargs["value"] == 0.85
        assert call_kwargs["data_type"] == "NUMERIC"
        assert call_kwargs["comment"] == "Test comment"

    def test_score_trace_boolean_type(self):
        """Arrange-Act-Assert: Verify boolean score uses correct values."""
        # Arrange
        mock_langfuse = Mock()

        # Act - True case
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="bool_score", value=1.0, data_type="BOOLEAN")

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["data_type"] == "BOOLEAN"

    def test_score_trace_categorical_type(self):
        """Arrange-Act-Assert: Verify categorical score accepts string values."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="category_score", value="success", data_type="CATEGORICAL")

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == "success"
        assert call_kwargs["data_type"] == "CATEGORICAL"

    def test_score_trace_with_metadata(self):
        """Arrange-Act-Assert: Verify metadata is passed to score."""
        # Arrange
        mock_langfuse = Mock()
        test_metadata = {"source": "test", "version": "1.0"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="meta_score", value=0.9, metadata=test_metadata)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["metadata"] == test_metadata

    def test_score_trace_without_optional_params(self):
        """Arrange-Act-Assert: Verify score works with minimal parameters."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="minimal", value=0.5)

        # Assert
        mock_langfuse.score_current_trace.assert_called_once()
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == "minimal"
        assert call_kwargs["value"] == 0.5
        assert call_kwargs["data_type"] == "NUMERIC"  # Default
        assert call_kwargs["comment"] is None
        assert call_kwargs["metadata"] is None


class TestScoreSpan:
    """Test suite for score_span function."""

    def test_score_span_records_correctly(self):
        """Arrange-Act-Assert: Verify span scoring works as expected."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_span(
                name="span_quality", value=0.95, data_type="NUMERIC", comment="High quality span"
            )

        # Assert
        mock_langfuse.score_current_span.assert_called_once()
        call_kwargs = mock_langfuse.score_current_span.call_args[1]
        assert call_kwargs["name"] == "span_quality"
        assert call_kwargs["value"] == 0.95
        assert call_kwargs["data_type"] == "NUMERIC"
        assert call_kwargs["comment"] == "High quality span"


class TestAddEvent:
    """Test suite for add_event function."""

    def test_add_event_with_full_params(self):
        """Arrange-Act-Assert: Verify event is added with all parameters."""
        # Arrange
        mock_langfuse = Mock()
        input_data = {"action": "triggered"}
        output_data = {"result": "success"}
        metadata = {"timestamp": "2024-01-01"}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_event(
                name="test_event", input_data=input_data, output_data=output_data, metadata=metadata
            )

        # Assert
        mock_langfuse.event.assert_called_once()
        call_kwargs = mock_langfuse.event.call_args[1]
        assert call_kwargs["name"] == "test_event"
        assert call_kwargs["input"] == input_data
        assert call_kwargs["output"] == output_data
        assert call_kwargs["metadata"] == metadata

    def test_add_event_with_minimal_params(self):
        """Arrange-Act-Assert: Verify event works with only name."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_event(name="simple_event")

        # Assert
        mock_langfuse.event.assert_called_once()
        call_kwargs = mock_langfuse.event.call_args[1]
        assert call_kwargs["name"] == "simple_event"
        assert call_kwargs["input"] is None
        assert call_kwargs["output"] is None
        assert call_kwargs["metadata"] is None


class TestUpdateTraceMetadata:
    """Test suite for update_trace_metadata function."""

    def test_update_trace_metadata_passes_correctly(self):
        """Arrange-Act-Assert: Verify metadata update is called correctly."""
        # Arrange
        mock_langfuse = Mock()
        new_metadata = {"updated_key": "updated_value", "new_field": 123}

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            update_trace_metadata(new_metadata)

        # Assert
        mock_langfuse.update_current_trace.assert_called_once()
        call_kwargs = mock_langfuse.update_current_trace.call_args[1]
        assert call_kwargs["metadata"] == new_metadata


class TestUpdateTraceTags:
    """Test suite for update_trace_tags function."""

    def test_update_trace_tags_passes_correctly(self):
        """Arrange-Act-Assert: Verify tags update is called correctly."""
        # Arrange
        mock_langfuse = Mock()
        new_tags = ["urgent", "escalated", "review_needed"]

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            update_trace_tags(new_tags)

        # Assert
        mock_langfuse.update_current_trace.assert_called_once()
        call_kwargs = mock_langfuse.update_current_trace.call_args[1]
        assert call_kwargs["tags"] == new_tags

    def test_update_trace_tags_with_empty_list(self):
        """Arrange-Act-Assert: Verify empty tags list is handled."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            update_trace_tags([])

        # Assert
        mock_langfuse.update_current_trace.assert_called_once()
        call_kwargs = mock_langfuse.update_current_trace.call_args[1]
        assert call_kwargs["tags"] == []


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_decorator_with_special_characters_in_session_id(self):
        """Arrange-Act-Assert: Verify special characters in session_id are handled."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        special_session = "session-with-dashes_and_underscores.123"

        @trace_customer_service(name="special_chars", session_id=special_session)
        async def handler():
            return "ok"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await handler()

        # Assert
        assert result == "ok"
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["session_id"] == special_session

    @pytest.mark.asyncio
    async def test_decorator_with_unicode_user_id(self):
        """Arrange-Act-Assert: Verify unicode user_id is hashed correctly."""
        # Arrange
        mock_langfuse = Mock()
        mock_update = Mock()
        mock_langfuse.update_current_trace = mock_update

        unicode_user = "用户_123_日本語"

        @trace_customer_service(name="unicode_test", user_id=unicode_user)
        async def handler():
            return "ok"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            result = await handler()

        # Assert
        assert result == "ok"
        call_kwargs = mock_update.call_args[1]
        assert "user_id" in call_kwargs
        # Should be a valid hash regardless of input encoding
        assert len(call_kwargs["user_id"]) == 16

    def test_score_trace_with_zero_value(self):
        """Arrange-Act-Assert: Verify zero value scores are accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="zero_score", value=0.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.0

    def test_score_trace_with_negative_value(self):
        """Arrange-Act-Assert: Verify negative values are accepted (no validation)."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="negative_score", value=-0.5)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == -0.5

    def test_score_trace_with_large_value(self):
        """Arrange-Act-Assert: Verify large values are accepted."""
        # Arrange
        mock_langfuse = Mock()
        large_value = 999999.99

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_trace(name="large_score", value=large_value)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == large_value

    def test_create_span_with_complex_metadata(self):
        """Arrange-Act-Assert: Verify complex nested metadata is handled."""
        # Arrange
        mock_langfuse = Mock()
        mock_span = Mock()
        mock_langfuse.start_span.return_value = mock_span

        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None,
        }

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            create_span(name="complex_meta", metadata=complex_metadata)

        # Assert
        call_kwargs = mock_langfuse.start_span.call_args[1]
        assert call_kwargs["metadata"] == complex_metadata

    def test_add_event_with_none_values(self):
        """Arrange-Act-Assert: Verify None values are properly passed."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_event(name="none_test", input_data=None, output_data=None, metadata=None)

        # Assert
        call_kwargs = mock_langfuse.event.call_args[1]
        assert call_kwargs["input"] is None
        assert call_kwargs["output"] is None
        assert call_kwargs["metadata"] is None
