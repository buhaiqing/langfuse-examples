"""
Concurrency tests for the observability platform.

Purpose:
- Test thread safety of session management
- Verify concurrent feedback submission
- Test async operations under load
- Ensure no race conditions or deadlocks

Test Strategy:
- Use ThreadPoolExecutor for concurrent execution
- Use asyncio for async concurrency tests
- Test with realistic concurrency levels (10-100 threads)
- Verify data integrity after concurrent operations

Dependencies:
- concurrent.futures
- asyncio
- threading
"""

import pytest
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch


class TestThreadSafety:
    """线程安全测试"""

    def test_concurrent_session_creation(self):
        """测试并发会话创建的线程安全性"""
        from src.observability.session import set_session, get_session_id, clear_session
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def create_and_verify_session(session_num):
            try:
                session_id = f"session_{session_num}"
                user_id = f"user_{session_num}"
                
                # Set session
                set_session(session_id=session_id, user_id=user_id)
                
                # Verify it was set correctly
                current_session = get_session_id()
                
                with lock:
                    results.append({
                        'session_num': session_num,
                        'expected': session_id,
                        'actual': current_session,
                        'match': current_session == session_id
                    })
                
                # Clean up
                clear_session()
                
            except Exception as e:
                with lock:
                    errors.append(f"Session {session_num}: {str(e)}")
        
        # Create 50 sessions concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_and_verify_session, i) 
                for i in range(50)
            ]
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result(timeout=10)
        
        print(f"Created {len(results)} sessions, {len(errors)} errors")
        
        # All should succeed without errors
        assert len(errors) == 0, f"Errors occurred: {errors[:5]}"
        assert len(results) == 50
        
        # All sessions should match their expected values
        matches = sum(1 for r in results if r['match'])
        print(f"Session matches: {matches}/{len(results)}")
        assert matches == 50, f"Only {matches}/50 sessions matched"

    def test_concurrent_feedback_submission(self):
        """测试并发反馈提交的线程安全性"""
        from src.observability.feedback import FeedbackCollector
        import uuid
        
        collector = FeedbackCollector()
        results = []
        errors = []
        lock = threading.Lock()
        
        def submit_feedback(feedback_num):
            try:
                trace_id = str(uuid.uuid4())
                
                if feedback_num % 3 == 0:
                    collector.record_acceptance(trace_id=trace_id, comment=f"Feedback {feedback_num}")
                    feedback_type = "acceptance"
                elif feedback_num % 3 == 1:
                    collector.record_rejection(trace_id=trace_id, reason="Not helpful")
                    feedback_type = "rejection"
                else:
                    collector.record_rating(trace_id=trace_id, rating=(feedback_num % 5) + 1)
                    feedback_type = "rating"
                
                with lock:
                    results.append(feedback_type)
                    
            except Exception as e:
                with lock:
                    errors.append(f"Feedback {feedback_num}: {str(e)}")
        
        # Submit 60 feedbacks concurrently
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(submit_feedback, i) 
                for i in range(60)
            ]
            
            for future in as_completed(futures):
                future.result(timeout=10)
        
        print(f"Submitted {len(results)} feedbacks, {len(errors)} errors")
        
        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors[:5]}"
        assert len(results) == 60
        
        # Check distribution
        acceptance_count = results.count("acceptance")
        rejection_count = results.count("rejection")
        rating_count = results.count("rating")
        
        print(f"Distribution: {acceptance_count} acceptances, {rejection_count} rejections, {rating_count} ratings")
        
        # Should have roughly equal distribution
        assert acceptance_count > 0
        assert rejection_count > 0
        assert rating_count > 0

    def test_concurrent_alert_checking(self):
        """测试并发告警检查的线程安全性"""
        from src.observability.alerting import AlertManager, AlertSeverity
        
        manager = AlertManager()
        results = []
        errors = []
        lock = threading.Lock()
        
        def check_alert(check_num):
            try:
                # Simulate checking different metrics
                metric_name = f"metric_{check_num % 5}"
                value = 0.5 + (check_num % 10) / 20  # Values between 0.5 and 1.0
                
                alert = manager.check_rule(
                    name=metric_name,
                    value=value,
                    threshold=0.8,
                    operator="lt",
                    severity=AlertSeverity.WARNING
                )
                
                with lock:
                    results.append({
                        'check_num': check_num,
                        'alert_triggered': alert is not None
                    })
                    
            except Exception as e:
                with lock:
                    errors.append(f"Check {check_num}: {str(e)}")
        
        # Run 40 checks concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(check_alert, i) 
                for i in range(40)
            ]
            
            for future in as_completed(futures):
                future.result(timeout=10)
        
        print(f"Completed {len(results)} checks, {len(errors)} errors")
        
        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors[:5]}"
        assert len(results) == 40


class TestAsyncOperations:
    """异步操作测试"""

    @pytest.mark.asyncio
    async def test_concurrent_async_tool_calls(self):
        """测试并发异步工具调用追踪"""
        from src.observability.decorators import observe_tool
        import asyncio
        
        call_results = []
        call_errors = []
        lock = asyncio.Lock()
        
        @observe_tool(name="test_tool")
        async def simulated_tool(tool_id: int, delay: float = 0.01):
            """Simulated tool with configurable delay"""
            await asyncio.sleep(delay)
            return {"tool_id": tool_id, "result": "success"}
        
        async def call_tool(tool_id):
            try:
                result = await simulated_tool(tool_id=tool_id, delay=0.01)
                async with lock:
                    call_results.append(result)
            except Exception as e:
                async with lock:
                    call_errors.append(str(e))
        
        # Execute 30 tool calls concurrently
        tasks = [call_tool(i) for i in range(30)]
        await asyncio.gather(*tasks)
        
        print(f"Completed {len(call_results)} tool calls, {len(call_errors)} errors")
        
        # All should succeed
        assert len(call_errors) == 0, f"Errors occurred: {call_errors[:5]}"
        assert len(call_results) == 30

    @pytest.mark.asyncio
    async def test_async_feedback_collection(self):
        """测试异步反馈收集的并发性"""
        from src.observability.feedback import FeedbackCollector
        import uuid
        import asyncio
        
        collector = FeedbackCollector()
        results = []
        errors = []
        lock = asyncio.Lock()
        
        async def submit_async_feedback(feedback_num):
            try:
                trace_id = str(uuid.uuid4())
                
                # Simulate some async work
                await asyncio.sleep(0.001)
                
                if feedback_num % 2 == 0:
                    collector.record_acceptance(trace_id=trace_id)
                    feedback_type = "acceptance"
                else:
                    collector.record_rating(trace_id=trace_id, rating=4)
                    feedback_type = "rating"
                
                async with lock:
                    results.append(feedback_type)
                    
            except Exception as e:
                async with lock:
                    errors.append(str(e))
        
        # Submit 40 feedbacks concurrently
        tasks = [submit_async_feedback(i) for i in range(40)]
        await asyncio.gather(*tasks)
        
        print(f"Submitted {len(results)} async feedbacks, {len(errors)} errors")
        
        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors[:5]}"
        assert len(results) == 40


class TestRaceConditions:
    """竞态条件测试"""

    def test_no_race_in_session_updates(self):
        """测试会话更新中无竞态条件"""
        from src.observability.session import set_session, get_session_id, clear_session
        
        final_sessions = {}
        barrier = threading.Barrier(10)  # Synchronize 10 threads
        
        def update_session(thread_id):
            try:
                # All threads wait at barrier
                barrier.wait(timeout=5)
                
                # Then all update simultaneously
                session_id = f"session_thread_{thread_id}"
                set_session(session_id=session_id, user_id=f"user_{thread_id}")
                
                # Read back immediately
                current = get_session_id()
                final_sessions[thread_id] = current
                
                # Cleanup
                clear_session()
                
            except Exception as e:
                final_sessions[thread_id] = f"ERROR: {e}"
        
        # Start 10 threads that will update simultaneously
        threads = []
        for i in range(10):
            t = threading.Thread(target=update_session, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        print(f"Final sessions: {len(final_sessions)}")
        
        # All should have completed
        assert len(final_sessions) == 10
        
        # No errors
        errors = [v for v in final_sessions.values() if isinstance(v, str) and v.startswith("ERROR")]
        assert len(errors) == 0, f"Race condition errors: {errors}"

    def test_concurrent_model_training_safety(self):
        """测试并发模型训练的安全性"""
        from src.observability.anomaly_detector import AnomalyDetector
        import pandas as pd
        import numpy as np
        
        detector = AnomalyDetector()
        training_results = []
        errors = []
        lock = threading.Lock()
        
        def train_model(thread_id):
            try:
                # Each thread trains on different data
                dates = pd.date_range(start='2024-01-01', periods=50, freq='10min')
                dates = dates.tz_localize(None)
                values = np.random.normal(100 + thread_id * 10, 5, 50)
                df = pd.DataFrame({'ds': dates, 'y': values})
                
                metric_name = f"metric_{thread_id}"
                detector._univariate_detector.train(metric_name, df)
                
                with lock:
                    training_results.append(thread_id)
                    
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Train 5 models concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(train_model, i) 
                for i in range(5)
            ]
            
            for future in as_completed(futures):
                future.result(timeout=30)
        
        print(f"Trained {len(training_results)} models, {len(errors)} errors")
        
        # All should succeed
        assert len(errors) == 0, f"Training errors: {errors}"
        assert len(training_results) == 5


class TestLoadHandling:
    """负载处理测试"""

    def test_high_frequency_metric_collection(self):
        """测试高频指标收集"""
        from src.observability.metrics_collector import MetricsCollector
        import time
        
        collector = MetricsCollector(window_minutes=10)
        
        start = time.perf_counter()
        
        # Collect metrics 100 times rapidly
        for i in range(100):
            success_rate = collector.collect_success_rate()
            latency = collector.collect_latency_p95()
            request_rate = collector.collect_request_rate()
            satisfaction = collector.collect_avg_satisfaction()
        
        elapsed = time.perf_counter() - start
        rate = 100 / elapsed if elapsed > 0 else float('inf')
        
        print(f"Collected metrics 100 times in {elapsed:.2f}s ({rate:.1f} collections/sec)")
        
        # Should handle high frequency collection
        assert elapsed < 10.0, f"Metric collection took {elapsed:.2f}s, expected < 10s"
        assert rate > 10, f"Collection rate {rate:.1f}/sec too slow"

    def test_smart_alert_manager_under_load(self):
        """测试 SmartAlertManager 在负载下的表现"""
        from src.observability.smart_alerting import SmartAlertManager
        
        manager = SmartAlertManager(detection_interval_minutes=10)
        
        errors = []
        lock = threading.Lock()
        
        def run_detection_cycle(cycle_num):
            try:
                manager._run_detection_cycle()
            except Exception as e:
                with lock:
                    errors.append(f"Cycle {cycle_num}: {str(e)}")
        
        # Run 10 detection cycles concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_detection_cycle, i) 
                for i in range(10)
            ]
            
            for future in as_completed(futures):
                future.result(timeout=60)
        
        print(f"Completed 10 concurrent detection cycles, {len(errors)} errors")
        
        # Should handle concurrent cycles gracefully
        assert len(errors) == 0, f"Errors under load: {errors[:5]}"
