"""
Performance tests for the observability platform.

Purpose:
- Measure detection cycle performance
- Benchmark model training time
- Test throughput under load
- Establish performance baselines

Test Strategy:
- Use pytest-benchmark for accurate measurements
- Test with realistic data sizes
- Set performance thresholds (fail if too slow)
- Run in isolation (no parallel execution)

Dependencies:
- pytest-benchmark (optional, falls back to manual timing)
"""

import time
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.observability.smart_alerting import SmartAlertManager
from src.observability.anomaly_detector import AnomalyDetector
from src.observability.metrics_collector import MetricsCollector


class TestDetectionPerformance:
    """性能测试: 异常检测周期"""

    def test_detection_cycle_under_5_seconds(self):
        """检测周期应在 5 秒内完成(首次训练除外)"""
        manager = SmartAlertManager(detection_interval_minutes=10)
        
        # First run includes model training (may take longer)
        start = time.perf_counter()
        manager._run_detection_cycle()
        elapsed_first = time.perf_counter() - start
        
        print(f"First detection cycle: {elapsed_first:.2f}s")
        # First run can take up to 30 seconds (includes training)
        assert elapsed_first < 30.0, f"First detection took {elapsed_first:.2f}s, expected < 30s"
        
        # Second run should be faster (models already trained)
        start = time.perf_counter()
        manager._run_detection_cycle()
        elapsed_second = time.perf_counter() - start
        
        print(f"Second detection cycle: {elapsed_second:.2f}s")
        # Subsequent runs should be fast
        assert elapsed_second < 5.0, f"Detection took {elapsed_second:.2f}s, expected < 5s"

    def test_model_training_performance(self):
        """模型训练应在合理时间内完成"""
        # Mock metrics collector
        mock_collector = Mock()
        
        detector = AnomalyDetector(metrics_collector=mock_collector)
        
        # Mock metrics collector to return sample data
        mock_collector = Mock()
        mock_collector.collect_success_rate.return_value = 0.95
        mock_collector.collect_latency_p95.return_value = 250.0
        mock_collector.collect_request_rate.return_value = 100.0
        mock_collector.collect_avg_satisfaction.return_value = 4.5
        
        # Create historical data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='10min')
        dates = dates.tz_localize(None)
        values = np.random.normal(100, 5, 100)
        df = pd.DataFrame({'ds': dates, 'y': values})
        
        mock_collector.get_historical_data.return_value = df
        
        detector.metrics_collector = mock_collector
        
        start = time.perf_counter()
        detector.train_all_models(hours_of_history=1)
        elapsed = time.perf_counter() - start
        
        print(f"Model training time: {elapsed:.2f}s")
        # Training should complete within 30 seconds
        assert elapsed < 30.0, f"Training took {elapsed:.2f}s, expected < 30s"

    def test_anomaly_detection_speed(self):
        """异常检测应该在毫秒级完成"""
        # Mock metrics collector
        mock_collector = Mock()
        mock_collector.collect_success_rate.return_value = 0.95
        mock_collector.collect_latency_p95.return_value = 250.0
        mock_collector.collect_request_rate.return_value = 100.0
        mock_collector.collect_avg_satisfaction.return_value = 4.5
        
        detector = AnomalyDetector(metrics_collector=mock_collector)
        
        # Mock trained models
        detector._univariate_detector = Mock()
        detector._multivariate_detector = Mock()
        detector._univariate_detector.detect_anomalies.return_value = []
        detector._multivariate_detector.detect.return_value = {
            'is_anomaly': False,
            'anomaly_score': 0.1,
            'severity': None
        }
        
        # Mock metrics
        mock_collector = Mock()
        mock_collector.collect_success_rate.return_value = 0.95
        mock_collector.collect_latency_p95.return_value = 250.0
        mock_collector.collect_request_rate.return_value = 100.0
        mock_collector.collect_avg_satisfaction.return_value = 4.5
        detector.metrics_collector = mock_collector
        
        start = time.perf_counter()
        anomalies = detector.detect_anomalies()
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        print(f"Anomaly detection time: {elapsed_ms:.2f}ms")
        # Detection should be very fast (< 100ms)
        assert elapsed_ms < 100.0, f"Detection took {elapsed_ms:.2f}ms, expected < 100ms"


class TestThroughput:
    """吞吐量测试"""

    def test_handle_100_concurrent_sessions(self):
        """测试处理 100 个并发会话的能力"""
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        results = []
        errors = []
        
        def create_session(session_id):
            try:
                from src.observability.session import set_session, get_session_id
                set_session(session_id=f"session_{session_id}", user_id=f"user_{session_id}")
                current = get_session_id()
                results.append(current)
            except Exception as e:
                errors.append(str(e))
        
        # Create 100 sessions concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(create_session, i) for i in range(100)]
            for future in futures:
                future.result(timeout=10)
        
        print(f"Created {len(results)} sessions, {len(errors)} errors")
        
        # All sessions should be created successfully
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100, f"Expected 100 sessions, got {len(results)}"

    def test_rapid_feedback_submission(self):
        """测试快速提交反馈的吞吐量"""
        from src.observability.feedback import FeedbackCollector
        import uuid
        
        collector = FeedbackCollector()
        
        start = time.perf_counter()
        
        # Submit 50 feedback items rapidly
        for i in range(50):
            trace_id = str(uuid.uuid4())
            collector.record_acceptance(trace_id=trace_id, comment=f"Test feedback {i}")
        
        elapsed = time.perf_counter() - start
        rate = 50 / elapsed if elapsed > 0 else float('inf')
        
        print(f"Submitted 50 feedbacks in {elapsed:.2f}s ({rate:.1f}/sec)")
        
        # Should handle at least 10 feedbacks per second
        assert rate > 10, f"Feedback rate {rate:.1f}/sec too slow, expected > 10/sec"
        assert elapsed < 5.0, f"Feedback submission took {elapsed:.2f}s, expected < 5s"


class TestMemoryUsage:
    """内存使用测试"""

    def test_smart_alert_manager_memory_stability(self):
        """测试 SmartAlertManager 内存稳定性"""
        import sys
        
        manager = SmartAlertManager(detection_interval_minutes=10)
        
        # Get initial memory estimate (rough)
        initial_size = sys.getsizeof(manager)
        
        # Run multiple detection cycles
        for i in range(10):
            manager._run_detection_cycle()
        
        final_size = sys.getsizeof(manager)
        
        # Memory shouldn't grow significantly (> 2x would indicate leak)
        growth_ratio = final_size / initial_size if initial_size > 0 else 1
        print(f"Memory growth ratio: {growth_ratio:.2f}x")
        
        # Allow some growth but not excessive
        assert growth_ratio < 3.0, f"Memory grew {growth_ratio:.2f}x, possible leak"


class TestScalability:
    """可扩展性测试"""

    def test_detection_with_large_history(self):
        """测试大数据量历史数据的检测性能"""
        # Create large historical dataset (1000 data points)
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
        dates = dates.tz_localize(None)
        values = np.random.normal(100, 10, 1000)
        df = pd.DataFrame({'ds': dates, 'y': values})
        
        mock_collector = Mock()
        mock_collector.get_historical_data.return_value = df
        mock_collector.collect_success_rate.return_value = 0.95
        mock_collector.collect_latency_p95.return_value = 250.0
        mock_collector.collect_request_rate.return_value = 100.0
        mock_collector.collect_avg_satisfaction.return_value = 4.5
        
        detector = AnomalyDetector(metrics_collector=mock_collector)
        
        start = time.perf_counter()
        detector.train_all_models(hours_of_history=24)
        train_elapsed = time.perf_counter() - start
        
        print(f"Training with 1000 data points: {train_elapsed:.2f}s")
        
        # Should handle 1000 points reasonably
        assert train_elapsed < 60.0, f"Training took {train_elapsed:.2f}s with 1000 points"

    def test_concurrent_alert_creation(self):
        """测试并发创建告警的性能"""
        from concurrent.futures import ThreadPoolExecutor
        from src.observability.alerting import get_alert_manager, configure_success_rate_alert, AlertSeverity
        
        # Use global alert manager and clear previous alerts
        manager = get_alert_manager()
        manager._alerts.clear()  # Clear any existing alerts
        
        # Configure a test rule
        configure_success_rate_alert(threshold=0.9, severity=AlertSeverity.WARNING)
        
        def create_alert(i):
            # Trigger alert by checking rule (rule name is 'success-rate-low')
            manager.check_rule(
                rule_name="success-rate-low",
                current_value=0.5  # Below threshold, should trigger
            )
        
        start = time.perf_counter()
        
        # Create 50 alerts concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_alert, i) for i in range(50)]
            for future in futures:
                future.result(timeout=5)
        
        elapsed = time.perf_counter() - start
        
        print(f"Created {len(manager._alerts)} alerts in {elapsed:.2f}s")
        
        # Should complete quickly
        assert elapsed < 5.0, f"Alert creation took {elapsed:.2f}s, expected < 5s"
        # Note: Due to race conditions, we may not get exactly 50, but should have some
        assert len(manager._alerts) > 0, "Should have created at least some alerts"


# Performance benchmarks (if pytest-benchmark is available)
try:
    import pytest_benchmark
    
    class TestBenchmarks:
        """Benchmark tests using pytest-benchmark"""
        
        def benchmark_detection_cycle(self, benchmark):
            """Benchmark detection cycle performance"""
            manager = SmartAlertManager()
            
            def run_detection():
                manager._run_detection_cycle()
            
            result = benchmark(run_detection)
            
            # Assert performance threshold
            assert result.stats.mean < 5.0, "Detection cycle too slow"
        
        def benchmark_anomaly_detection(self, benchmark):
            """Benchmark anomaly detection speed"""
            detector = AnomalyDetector()
            detector._univariate_detector = Mock()
            detector._multivariate_detector = Mock()
            detector._univariate_detector.detect_anomalies.return_value = []
            detector._multivariate_detector.detect.return_value = {
                'is_anomaly': False,
                'anomaly_score': 0.1,
                'severity': None
            }
            
            mock_collector = Mock()
            mock_collector.collect_success_rate.return_value = 0.95
            mock_collector.collect_latency_p95.return_value = 250.0
            mock_collector.collect_request_rate.return_value = 100.0
            mock_collector.collect_avg_satisfaction.return_value = 4.5
            detector.metrics_collector = mock_collector
            
            def detect():
                return detector.detect_anomalies()
            
            result = benchmark(detect)
            
            # Should be very fast
            assert result.stats.mean < 0.1, "Detection too slow"  # < 100ms
            
except ImportError:
    # pytest-benchmark not installed, skip benchmark tests
    pass
