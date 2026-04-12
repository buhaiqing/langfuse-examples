"""
Anomaly detection engine using Prophet and PyOD.

Provides time series anomaly detection with Prophet and multivariate
anomaly detection with PyOD (Isolation Forest, LOF).
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from prophet import Prophet
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from sklearn.preprocessing import StandardScaler

from src.observability.alerting import AlertSeverity
from src.observability.metrics_collector import MetricsCollector


class TimeSeriesAnomalyDetector:
    """
    Time series anomaly detection using Prophet.
    
    Detects anomalies by comparing actual values against predicted
    confidence intervals from Prophet's forecasting model.
    """

    def __init__(self, uncertainty_samples: int = 100):
        """
        Initialize the time series detector.
        
        Args:
            uncertainty_samples: Number of samples for uncertainty estimation.
        """
        self.uncertainty_samples = uncertainty_samples
        self._models: Dict[str, Prophet] = {}

    def train(self, metric_name: str, historical_data: pd.DataFrame) -> None:
        """
        Train a Prophet model for a specific metric.
        
        Args:
            metric_name: Name of the metric.
            historical_data: DataFrame with columns ['ds', 'y'] where:
                - ds: datetime
                - y: metric value
        """
        if len(historical_data) < 50:
            print(
                f"Warning: Insufficient data for {metric_name} "
                f"({len(historical_data)} points, need at least 50)"
            )
            return

        model = Prophet(
            interval_width=0.95,  # 95% confidence interval
            uncertainty_samples=self.uncertainty_samples,
            daily_seasonality=True,
            weekly_seasonality=True,
        )
        model.fit(historical_data)
        self._models[metric_name] = model

    def detect_anomalies(
        self,
        metric_name: str,
        current_value: float,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Detect if the current value is anomalous.
        
        Args:
            metric_name: Name of the metric.
            current_value: Current metric value.
            timestamp: Timestamp for prediction (defaults to now).
            
        Returns:
            Dictionary containing:
                - is_anomaly: bool
                - expected_range: tuple (lower, upper)
                - deviation_score: float (deviation from expected)
                - severity: AlertSeverity
                - expected_value: float
        """
        model = self._models.get(metric_name)
        if not model:
            raise ValueError(f"No model trained for {metric_name}")

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Make prediction
        future = pd.DataFrame({'ds': [timestamp]})
        forecast = model.predict(future)

        lower = forecast['yhat_lower'].iloc[0]
        upper = forecast['yhat_upper'].iloc[0]
        expected = forecast['yhat'].iloc[0]

        # Determine if anomalous
        is_anomaly = current_value < lower or current_value > upper

        # Calculate deviation score
        deviation = abs(current_value - expected)
        range_width = upper - lower
        deviation_score = deviation / range_width if range_width > 0 else 0

        # Determine severity based on deviation
        if deviation_score > 3:
            severity = AlertSeverity.CRITICAL
        elif deviation_score > 2:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        return {
            'is_anomaly': is_anomaly,
            'expected_range': (float(lower), float(upper)),
            'deviation_score': float(deviation_score),
            'severity': severity,
            'expected_value': float(expected)
        }


class MultivariateAnomalyDetector:
    """
    Multivariate anomaly detection using PyOD.
    
    Detects anomalies in multi-dimensional feature space using
    Isolation Forest or Local Outlier Factor (LOF).
    """

    def __init__(
        self,
        method: str = 'iforest',
        contamination: float = 0.05
    ):
        """
        Initialize the multivariate detector.
        
        Args:
            method: Detection method ('iforest' or 'lof').
            contamination: Expected proportion of outliers in the data.
        """
        self.method = method
        self.contamination = contamination
        self._scaler = StandardScaler()
        self._detector = None
        self._is_fitted = False

    def train(self, historical_features: np.ndarray) -> None:
        """
        Train the anomaly detection model.
        
        Args:
            historical_features: Feature matrix of shape (n_samples, n_features).
                Features should be: [success_rate, latency_p95, request_rate, satisfaction]
        """
        if len(historical_features) < 50:
            print(
                f"Warning: Insufficient data for training "
                f"({len(historical_features)} samples, need at least 50)"
            )
            return

        # Standardize features
        scaled_data = self._scaler.fit_transform(historical_features)

        # Initialize detector
        if self.method == 'iforest':
            self._detector = IForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
        elif self.method == 'lof':
            self._detector = LOF(
                contamination=self.contamination,
                n_neighbors=20
            )
        else:
            raise ValueError(f"Unknown method: {self.method}")

        # Train
        self._detector.fit(scaled_data)
        self._is_fitted = True

    def detect(self, current_features: np.ndarray) -> Dict[str, Any]:
        """
        Detect if the current feature vector is anomalous.
        
        Args:
            current_features: Feature vector of shape (1, n_features).
            
        Returns:
            Dictionary containing:
                - is_anomaly: bool
                - anomaly_score: float (0-1, higher = more anomalous)
                - severity: AlertSeverity
        """
        if not self._is_fitted:
            raise RuntimeError("Model not trained")

        # Standardize
        scaled = self._scaler.transform(current_features)

        # Predict
        prediction = self._detector.predict(scaled)  # 0 (normal) or 1 (anomaly)
        score = self._detector.decision_function(scaled)[0]

        is_anomaly = prediction[0] == 1

        # Determine severity based on anomaly score
        if score > 0.8:
            severity = AlertSeverity.CRITICAL
        elif score > 0.6:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': float(score),
            'severity': severity
        }


class AnomalyDetector:
    """
    Unified anomaly detection engine combining multiple methods.
    
    Orchestrates time series and multivariate anomaly detection,
    providing a comprehensive view of system health.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize the anomaly detector.
        
        Args:
            metrics_collector: Metrics collector instance.
        """
        self.metrics_collector = metrics_collector
        self.ts_detector = TimeSeriesAnomalyDetector()
        self.mv_detector = MultivariateAnomalyDetector(method='iforest')
        self._trained_metrics: Set[str] = set()

    def train_all_models(self, hours_of_history: int = 24) -> None:
        """
        Train all detection models.
        
        Args:
            hours_of_history: Number of hours of historical data to use.
        """
        print(f"Training anomaly detection models ({hours_of_history}h history)...")

        # Train time series models for each metric
        metrics = ['success_rate', 'latency_p95', 'request_rate']
        
        for metric in metrics:
            try:
                historical_data = self.metrics_collector.get_historical_data(
                    metric, hours=hours_of_history
                )
                
                if len(historical_data) >= 50:
                    self.ts_detector.train(metric, historical_data)
                    self._trained_metrics.add(metric)
                    print(f"  ✓ Trained model for {metric} "
                          f"({len(historical_data)} data points)")
                else:
                    print(f"  ✗ Insufficient data for {metric} "
                          f"({len(historical_data)} points)")
                    
            except Exception as e:
                print(f"  ✗ Failed to train model for {metric}: {e}")

        # Train multivariate model
        try:
            features = self._prepare_multivariate_features(hours_of_history)
            if len(features) >= 50:
                self.mv_detector.train(features)
                print(f"  ✓ Trained multivariate model "
                      f"({len(features)} samples)")
            else:
                print(f"  ✗ Insufficient data for multivariate model "
                      f"({len(features)} samples)")
        except Exception as e:
            print(f"  ✗ Failed to train multivariate model: {e}")

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Execute anomaly detection across all metrics.
        
        Returns:
            List of detected anomalies with details.
        """
        anomalies = []

        # 1. Univariate time series detection
        for metric in self._trained_metrics:
            try:
                current_value = self._get_current_metric_value(metric)
                result = self.ts_detector.detect_anomalies(
                    metric, current_value, datetime.now(timezone.utc)
                )

                if result['is_anomaly']:
                    anomalies.append({
                        'type': 'univariate',
                        'metric': metric,
                        'current_value': current_value,
                        **result
                    })
            except Exception as e:
                print(f"Failed to detect anomalies for {metric}: {e}")

        # 2. Multivariate detection
        try:
            current_features = self._get_current_feature_vector()
            mv_result = self.mv_detector.detect(current_features)

            if mv_result['is_anomaly']:
                anomalies.append({
                    'type': 'multivariate',
                    'features': {
                        'success_rate': float(current_features[0][0]),
                        'latency_p95': float(current_features[0][1]),
                        'request_rate': float(current_features[0][2]),
                        'satisfaction': float(current_features[0][3]) 
                                       if current_features[0][3] >= 0 else 0.0,
                    },
                    **mv_result
                })
        except Exception as e:
            print(f"Failed to perform multivariate detection: {e}")

        return anomalies

    def _prepare_multivariate_features(
        self,
        hours: int
    ) -> np.ndarray:
        """
        Prepare multivariate feature matrix from historical data.
        
        Args:
            hours: Number of hours of historical data.
            
        Returns:
            Feature matrix of shape (n_samples, 4).
        """
        # Collect historical data for all metrics
        metrics = ['success_rate', 'latency_p95', 'request_rate']
        dataframes = {}
        
        for metric in metrics:
            df = self.metrics_collector.get_historical_data(
                metric, hours=hours
            )
            if len(df) > 0:
                dataframes[metric] = df

        if not dataframes:
            return np.array([])

        # Align timestamps and create feature matrix
        # For simplicity, use the shortest dataframe's length
        min_length = min(len(df) for df in dataframes.values())
        
        features = []
        for i in range(min_length):
            row = []
            for metric in metrics:
                if metric in dataframes and i < len(dataframes[metric]):
                    row.append(dataframes[metric].iloc[i]['y'])
                else:
                    row.append(0.0)
            
            # Add satisfaction (may be None)
            satisfaction = self.metrics_collector.collect_avg_satisfaction()
            row.append(satisfaction if satisfaction is not None else 0.0)
            
            features.append(row)

        return np.array(features)

    def _get_current_metric_value(self, metric: str) -> float:
        """
        Get current value for a specific metric.
        
        Args:
            metric: Metric name.
            
        Returns:
            Current metric value.
        """
        if metric == 'success_rate':
            return self.metrics_collector.collect_success_rate()
        elif metric == 'latency_p95':
            return self.metrics_collector.collect_latency_p95()
        elif metric == 'request_rate':
            return self.metrics_collector.collect_request_rate()
        else:
            return 0.0

    def _get_current_feature_vector(self) -> np.ndarray:
        """
        Get current feature vector for multivariate detection.
        
        Returns:
            Feature vector of shape (1, 4).
        """
        satisfaction = self.metrics_collector.collect_avg_satisfaction()
        
        return np.array([[
            self.metrics_collector.collect_success_rate(),
            self.metrics_collector.collect_latency_p95(),
            self.metrics_collector.collect_request_rate(),
            satisfaction if satisfaction is not None else 0.0
        ]])
