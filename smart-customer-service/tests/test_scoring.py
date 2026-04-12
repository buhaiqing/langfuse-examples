"""
Tests for the standardized scoring system.

This module tests all scoring functions including:
- Intent confidence scoring
- Retrieval relevance scoring
- Tool success rate scoring
- Issue resolution scoring (BOOLEAN)
- User satisfaction scoring (Likert scale)
- Failure type categorization (CATEGORICAL)
- Response latency scoring
- Dialogue coherence scoring
- Slot completion rate scoring
- Escalation scoring
- First contact resolution scoring
- Comprehensive scoring
"""

from unittest.mock import Mock, patch

import pytest

from core.scoring import (
    ANSWER_CORRECTNESS,
    ANSWER_HELPFULNESS,
    DIALOGUE_COHERENCE,
    ESCALATION_REASON,
    ESCALATION_REQUIRED,
    FAILURE_TYPE,
    FIRST_CONTACT_RESOLUTION,
    # Constants
    INTENT_CONFIDENCE,
    ISSUE_RESOLVED,
    RESPONSE_LATENCY_MS,
    RETRIEVAL_RELEVANCE,
    SLOT_COMPLETION_RATE,
    TOOL_SUCCESS_RATE,
    USER_SATISFACTION,
    add_comprehensive_scores,
    score_dialogue_coherence,
    score_escalation_required,
    score_failure_type,
    score_first_contact_resolution,
    score_intent_confidence,
    score_issue_resolved,
    score_response_latency,
    score_retrieval_relevance,
    score_slot_completion_rate,
    score_tool_success_rate,
    score_user_satisfaction,
)


class TestScoreIntentConfidence:
    """Test suite for intent confidence scoring."""

    def test_score_intent_confidence_valid_range(self):
        """Arrange-Act-Assert: Verify valid confidence values are scored correctly."""
        # Arrange
        mock_langfuse = Mock()
        test_values = [0.0, 0.5, 0.85, 0.99, 1.0]

        # Act & Assert
        for value in test_values:
            with patch("core.tracing.langfuse", mock_langfuse):
                score_intent_confidence(value)

            call_kwargs = mock_langfuse.score_current_trace.call_args[1]
            assert call_kwargs["name"] == INTENT_CONFIDENCE
            assert call_kwargs["value"] == value
            assert call_kwargs["data_type"] == "NUMERIC"
            mock_langfuse.reset_mock()

    def test_score_intent_confidence_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment is used when provided."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "High confidence classification"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.95, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment

    def test_score_intent_confidence_default_comment(self):
        """Arrange-Act-Assert: Verify default comment format when none provided."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.75)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert "Intent confidence: 0.75" in call_kwargs["comment"]

    def test_score_intent_confidence_boundary_zero(self):
        """Arrange-Act-Assert: Verify zero confidence is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.0

    def test_score_intent_confidence_boundary_one(self):
        """Arrange-Act-Assert: Verify maximum confidence is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(1.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 1.0


class TestScoreRetrievalRelevance:
    """Test suite for RAG retrieval relevance scoring."""

    def test_score_retrieval_relevance_normal_case(self):
        """Arrange-Act-Assert: Verify normal relevance scores work correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_retrieval_relevance(0.88)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == RETRIEVAL_RELEVANCE
        assert call_kwargs["value"] == 0.88
        assert call_kwargs["data_type"] == "NUMERIC"

    def test_score_retrieval_relevance_with_comment(self):
        """Arrange-Act-Assert: Verify custom comment overrides default."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Excellent document match"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_retrieval_relevance(0.92, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment


class TestScoreToolSuccessRate:
    """Test suite for tool execution success rate scoring."""

    def test_score_tool_success_rate_full_success(self):
        """Arrange-Act-Assert: Verify 100% success rate is scored correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_tool_success_rate(1.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == TOOL_SUCCESS_RATE
        assert call_kwargs["value"] == 1.0

    def test_score_tool_success_rate_partial_success(self):
        """Arrange-Act-Assert: Verify partial success rate is scored correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_tool_success_rate(0.67)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.67

    def test_score_tool_success_rate_zero_success(self):
        """Arrange-Act-Assert: Verify 0% success rate is handled."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_tool_success_rate(0.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.0


class TestScoreIssueResolved:
    """Test suite for issue resolution BOOLEAN scoring."""

    def test_score_issue_resolved_true(self):
        """Arrange-Act-Assert: Verify resolved=True maps to value 1.0."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_issue_resolved(True)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == ISSUE_RESOLVED
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["data_type"] == "BOOLEAN"
        assert "Issue resolved" in call_kwargs["comment"]

    def test_score_issue_resolved_false(self):
        """Arrange-Act-Assert: Verify resolved=False maps to value 0.0."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_issue_resolved(False)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == ISSUE_RESOLVED
        assert call_kwargs["value"] == 0.0
        assert call_kwargs["data_type"] == "BOOLEAN"
        assert "Issue not resolved" in call_kwargs["comment"]

    def test_score_issue_resolved_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment is used for resolved case."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Customer confirmed issue fixed"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_issue_resolved(True, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment


class TestScoreUserSatisfaction:
    """Test suite for user satisfaction Likert scale scoring."""

    def test_score_user_satisfaction_all_valid_ratings(self):
        """Arrange-Act-Assert: Verify all valid ratings (1-5) are accepted."""
        # Arrange
        mock_langfuse = Mock()
        valid_ratings = [1, 2, 3, 4, 5]

        # Act & Assert
        for rating in valid_ratings:
            with patch("core.tracing.langfuse", mock_langfuse):
                score_user_satisfaction(rating)

            call_kwargs = mock_langfuse.score_current_trace.call_args[1]
            assert call_kwargs["name"] == USER_SATISFACTION
            assert call_kwargs["value"] == float(rating)
            assert call_kwargs["data_type"] == "NUMERIC"
            mock_langfuse.reset_mock()

    def test_score_user_satisfaction_minimum_rating(self):
        """Arrange-Act-Assert: Verify minimum rating (1) is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_user_satisfaction(1)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 1.0

    def test_score_user_satisfaction_maximum_rating(self):
        """Arrange-Act-Assert: Verify maximum rating (5) is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_user_satisfaction(5)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 5.0

    def test_score_user_satisfaction_below_range_raises_error(self):
        """Arrange-Act-Assert: Verify rating below 1 raises ValueError."""
        # Arrange
        invalid_ratings = [0, -1, -5]

        # Act & Assert
        for rating in invalid_ratings:
            with pytest.raises(ValueError) as exc_info:
                score_user_satisfaction(rating)
            assert f"Satisfaction rating must be 1-5, got {rating}" in str(exc_info.value)

    def test_score_user_satisfaction_above_range_raises_error(self):
        """Arrange-Act-Assert: Verify rating above 5 raises ValueError."""
        # Arrange
        invalid_ratings = [6, 10, 100]

        # Act & Assert
        for rating in invalid_ratings:
            with pytest.raises(ValueError) as exc_info:
                score_user_satisfaction(rating)
            assert f"Satisfaction rating must be 1-5, got {rating}" in str(exc_info.value)

    def test_score_user_satisfaction_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment is used when provided."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Very satisfied with service"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_user_satisfaction(5, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment

    def test_score_user_satisfaction_default_comment_format(self):
        """Arrange-Act-Assert: Verify default comment includes rating."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_user_satisfaction(4)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert "User satisfaction: 4/5" in call_kwargs["comment"]


class TestScoreFailureType:
    """Test suite for failure type CATEGORICAL scoring."""

    def test_score_failure_type_all_valid_types(self):
        """Arrange-Act-Assert: Verify all valid failure types are accepted."""
        # Arrange
        mock_langfuse = Mock()
        valid_types = [
            "intent_recognition_error",
            "rag_retrieval_failure",
            "tool_call_failure",
            "generation_quality_issue",
            "user_experience_issue",
            "none",
        ]

        # Act & Assert
        for failure_type in valid_types:
            with patch("core.tracing.langfuse", mock_langfuse):
                score_failure_type(failure_type)

            call_kwargs = mock_langfuse.score_current_trace.call_args[1]
            assert call_kwargs["name"] == FAILURE_TYPE
            assert call_kwargs["value"] == failure_type
            assert call_kwargs["data_type"] == "CATEGORICAL"
            mock_langfuse.reset_mock()

    def test_score_failure_type_invalid_type_raises_error(self):
        """Arrange-Act-Assert: Verify invalid failure type raises ValueError."""
        # Arrange
        invalid_types = ["unknown_error", "random_failure", ""]

        # Act & Assert
        for failure_type in invalid_types:
            with pytest.raises(ValueError) as exc_info:
                score_failure_type(failure_type)
            assert "Invalid failure type" in str(exc_info.value)

    def test_score_failure_type_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment is used when provided."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Specific error details here"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_failure_type("tool_call_failure", comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment

    def test_score_failure_type_default_comment_format(self):
        """Arrange-Act-Assert: Verify default comment includes failure type."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_failure_type("intent_recognition_error")

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert "Failure type: intent_recognition_error" in call_kwargs["comment"]

    def test_score_failure_type_none_indicates_no_failure(self):
        """Arrange-Act-Assert: Verify 'none' type indicates no failure."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_failure_type("none")

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == "none"


class TestScoreResponseLatency:
    """Test suite for response latency scoring."""

    def test_score_response_latency_normal_value(self):
        """Arrange-Act-Assert: Verify normal latency values are scored correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(250.5)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == RESPONSE_LATENCY_MS
        assert call_kwargs["value"] == 250.5
        assert call_kwargs["data_type"] == "NUMERIC"

    def test_score_response_latency_zero_latency(self):
        """Arrange-Act-Assert: Verify zero latency is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(0.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.0

    def test_score_response_latency_high_latency(self):
        """Arrange-Act-Assert: Verify high latency values are accepted."""
        # Arrange
        mock_langfuse = Mock()
        high_latency = 5000.0  # 5 seconds

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(high_latency)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == high_latency

    def test_score_response_latency_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment is used when provided."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Slow response due to complex query"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(1500.0, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment


class TestScoreDialogueCoherence:
    """Test suite for dialogue coherence scoring."""

    def test_score_dialogue_coherence_valid_range(self):
        """Arrange-Act-Assert: Verify coherence values in 0-1 range are accepted."""
        # Arrange
        mock_langfuse = Mock()
        test_values = [0.0, 0.25, 0.5, 0.75, 1.0]

        # Act & Assert
        for value in test_values:
            with patch("core.tracing.langfuse", mock_langfuse):
                score_dialogue_coherence(value)

            call_kwargs = mock_langfuse.score_current_trace.call_args[1]
            assert call_kwargs["name"] == DIALOGUE_COHERENCE
            assert call_kwargs["value"] == value
            mock_langfuse.reset_mock()


class TestScoreSlotCompletionRate:
    """Test suite for slot completion rate scoring."""

    def test_score_slot_completion_rate_full_completion(self):
        """Arrange-Act-Assert: Verify 100% completion rate is scored correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_slot_completion_rate(1.0)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == SLOT_COMPLETION_RATE
        assert call_kwargs["value"] == 1.0

    def test_score_slot_completion_rate_partial_completion(self):
        """Arrange-Act-Assert: Verify partial completion is scored correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_slot_completion_rate(0.6)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.6


class TestScoreEscalationRequired:
    """Test suite for escalation required BOOLEAN scoring."""

    def test_score_escalation_required_true_without_reason(self):
        """Arrange-Act-Assert: Verify escalation=True without reason works."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_escalation_required(True)

        # Assert
        calls = mock_langfuse.score_current_trace.call_args_list
        assert len(calls) == 1
        first_call = calls[0][1]
        assert first_call["name"] == ESCALATION_REQUIRED
        assert first_call["value"] == 1.0
        assert first_call["data_type"] == "BOOLEAN"

    def test_score_escalation_required_true_with_reason(self):
        """Arrange-Act-Assert: Verify escalation=True with reason creates two scores."""
        # Arrange
        mock_langfuse = Mock()
        reason = "low_confidence_intent"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_escalation_required(True, reason=reason)

        # Assert
        calls = mock_langfuse.score_current_trace.call_args_list
        assert len(calls) == 2

        # First call: escalation_required
        first_call = calls[0][1]
        assert first_call["name"] == ESCALATION_REQUIRED
        assert first_call["value"] == 1.0

        # Second call: escalation_reason
        second_call = calls[1][1]
        assert second_call["name"] == ESCALATION_REASON
        assert second_call["value"] == reason
        assert second_call["data_type"] == "CATEGORICAL"

    def test_score_escalation_required_false(self):
        """Arrange-Act-Assert: Verify escalation=False only creates one score."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_escalation_required(False)

        # Assert
        calls = mock_langfuse.score_current_trace.call_args_list
        assert len(calls) == 1
        first_call = calls[0][1]
        assert first_call["name"] == ESCALATION_REQUIRED
        assert first_call["value"] == 0.0

    def test_score_escalation_required_false_with_reason_ignored(self):
        """Arrange-Act-Assert: Verify reason is ignored when escalation=False."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_escalation_required(False, reason="some reason")

        # Assert
        calls = mock_langfuse.score_current_trace.call_args_list
        assert len(calls) == 1  # Only ESCALATION_REQUIRED, not ESCALATION_REASON
        first_call = calls[0][1]
        assert first_call["name"] == ESCALATION_REQUIRED
        assert first_call["value"] == 0.0


class TestScoreFirstContactResolution:
    """Test suite for first contact resolution BOOLEAN scoring."""

    def test_score_first_contact_resolution_true(self):
        """Arrange-Act-Assert: Verify FCR=True maps to value 1.0."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_first_contact_resolution(True)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == FIRST_CONTACT_RESOLUTION
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["data_type"] == "BOOLEAN"
        assert "Resolved on first contact" in call_kwargs["comment"]

    def test_score_first_contact_resolution_false(self):
        """Arrange-Act-Assert: Verify FCR=False maps to value 0.0."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_first_contact_resolution(False)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["name"] == FIRST_CONTACT_RESOLUTION
        assert call_kwargs["value"] == 0.0
        assert call_kwargs["data_type"] == "BOOLEAN"
        assert "Required multiple contacts" in call_kwargs["comment"]

    def test_score_first_contact_resolution_with_custom_comment(self):
        """Arrange-Act-Assert: Verify custom comment overrides default."""
        # Arrange
        mock_langfuse = Mock()
        custom_comment = "Quick resolution without follow-up"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_first_contact_resolution(True, comment=custom_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == custom_comment


class TestAddComprehensiveScores:
    """Test suite for comprehensive scoring function."""

    def test_add_comprehensive_scores_all_parameters(self):
        """Arrange-Act-Assert: Verify all parameters trigger their respective scores."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_comprehensive_scores(
                intent_confidence=0.9,
                retrieval_relevance=0.85,
                tool_success_rate=1.0,
                issue_resolved=True,
                user_satisfaction=4,
                response_latency_ms=300.0,
                failure_type="none",
                escalation_required=False,
            )

        # Assert
        assert mock_langfuse.score_current_trace.call_count == 8

    def test_add_comprehensive_scores_only_some_parameters(self):
        """Arrange-Act-Assert: Verify only provided parameters are scored."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_comprehensive_scores(intent_confidence=0.8, issue_resolved=True)

        # Assert
        assert mock_langfuse.score_current_trace.call_count == 2

    def test_add_comprehensive_scores_no_parameters(self):
        """Arrange-Act-Assert: Verify no scores when all parameters are None."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_comprehensive_scores()

        # Assert
        mock_langfuse.score_current_trace.assert_not_called()

    def test_add_comprehensive_scores_with_escalation_reason(self):
        """Arrange-Act-Assert: Verify escalation reason creates additional score."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_comprehensive_scores(
                escalation_required=True, escalation_reason="complex_technical_issue"
            )

        # Assert
        # ESCALATION_REQUIRED + ESCALATION_REASON = 2 calls
        assert mock_langfuse.score_current_trace.call_count == 2

    def test_add_comprehensive_scores_user_satisfaction_validation(self):
        """Arrange-Act-Assert: Verify invalid satisfaction rating raises error."""
        # Arrange
        mock_langfuse = Mock()

        # Act & Assert
        with patch("core.tracing.langfuse", mock_langfuse):
            with pytest.raises(ValueError):
                add_comprehensive_scores(user_satisfaction=6)

    def test_add_comprehensive_scores_failure_type_validation(self):
        """Arrange-Act-Assert: Verify invalid failure type raises error."""
        # Arrange
        mock_langfuse = Mock()

        # Act & Assert
        with patch("core.tracing.langfuse", mock_langfuse):
            with pytest.raises(ValueError):
                add_comprehensive_scores(failure_type="invalid_type")


class TestScoringConstants:
    """Test suite for scoring constant values."""

    def test_constants_are_defined(self):
        """Arrange-Act-Assert: Verify all expected constants exist and have correct values."""
        # Arrange & Act & Assert
        assert INTENT_CONFIDENCE == "intent_confidence"
        assert RETRIEVAL_RELEVANCE == "retrieval_relevance"
        assert TOOL_SUCCESS_RATE == "tool_success_rate"
        assert ISSUE_RESOLVED == "issue_resolved"
        assert USER_SATISFACTION == "user_satisfaction"
        assert FAILURE_TYPE == "failure_type"
        assert RESPONSE_LATENCY_MS == "response_latency_ms"
        assert DIALOGUE_COHERENCE == "dialogue_coherence"
        assert SLOT_COMPLETION_RATE == "slot_completion_rate"
        assert ESCALATION_REQUIRED == "escalation_required"
        assert ESCALATION_REASON == "escalation_reason"
        assert FIRST_CONTACT_RESOLUTION == "first_contact_resolution"
        assert ANSWER_CORRECTNESS == "answer_correctness"
        assert ANSWER_HELPFULNESS == "answer_helpfulness"


class TestEdgeCases:
    """Test edge cases and boundary conditions for scoring."""

    def test_score_intent_confidence_very_small_value(self):
        """Arrange-Act-Assert: Verify very small positive values are accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.0001)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.0001

    def test_score_response_latency_fractional_ms(self):
        """Arrange-Act-Assert: Verify fractional millisecond values are accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(0.5)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 0.5

    def test_score_response_latency_very_high_value(self):
        """Arrange-Act-Assert: Verify very high latency values are accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(60000.0)  # 60 seconds

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["value"] == 60000.0

    def test_score_failure_type_case_sensitive(self):
        """Arrange-Act-Assert: Verify failure type is case-sensitive."""
        # Arrange
        mock_langfuse = Mock()

        # Act & Assert - uppercase should fail
        with pytest.raises(ValueError):
            score_failure_type("INTENT_RECOGNITION_ERROR")

    def test_score_user_satisfaction_float_rejected(self):
        """Arrange-Act-Assert: Verify float ratings outside 1-5 range are rejected."""
        # Arrange
        mock_langfuse = Mock()

        # Act & Assert - floats outside 1-5 range should fail
        # Note: 3.5 is within 1-5 range numerically, so it passes the check
        # Only values < 1 or > 5 are rejected
        with pytest.raises(ValueError):
            score_user_satisfaction(0.5)  # Below minimum

        with pytest.raises(ValueError):
            score_user_satisfaction(5.5)  # Above maximum

    def test_multiple_scores_same_name(self):
        """Arrange-Act-Assert: Verify multiple scores with same name can be added."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.8)
            score_intent_confidence(0.9)

        # Assert
        assert mock_langfuse.score_current_trace.call_count == 2
        calls = mock_langfuse.score_current_trace.call_args_list
        assert calls[0][1]["value"] == 0.8
        assert calls[1][1]["value"] == 0.9

    def test_score_with_special_characters_in_comment(self):
        """Arrange-Act-Assert: Verify special characters in comments are handled."""
        # Arrange
        mock_langfuse = Mock()
        special_comment = 'Error: "Connection timeout" - retry needed!'

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_response_latency(5000.0, comment=special_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == special_comment

    def test_score_with_unicode_in_comment(self):
        """Arrange-Act-Assert: Verify unicode characters in comments are handled."""
        # Arrange
        mock_langfuse = Mock()
        unicode_comment = "用户满意度: 非常满意"

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_user_satisfaction(5, comment=unicode_comment)

        # Assert
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert call_kwargs["comment"] == unicode_comment

    def test_score_with_empty_string_comment(self):
        """Arrange-Act-Assert: Verify empty string comment is accepted."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            score_intent_confidence(0.75, comment="")

        # Assert
        # Note: The scoring function uses `comment or default_comment` pattern,
        # so empty string is falsy and falls back to default comment
        call_kwargs = mock_langfuse.score_current_trace.call_args[1]
        assert "Intent confidence" in call_kwargs["comment"]

    def test_add_comprehensive_scores_mixed_none_and_values(self):
        """Arrange-Act-Assert: Verify mix of None and valid values works correctly."""
        # Arrange
        mock_langfuse = Mock()

        # Act
        with patch("core.tracing.langfuse", mock_langfuse):
            add_comprehensive_scores(
                intent_confidence=0.9,  # Valid
                retrieval_relevance=None,  # Skip
                tool_success_rate=0.8,  # Valid
                issue_resolved=None,  # Skip
                user_satisfaction=4,  # Valid
            )

        # Assert
        # Only 3 scores should be created
        assert mock_langfuse.score_current_trace.call_count == 3
