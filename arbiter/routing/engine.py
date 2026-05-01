"""Intelligent routing engine with predictive circuit breaker.

Core component that simulates real-time routing decisions based on
ML-predicted latency and contextual signals.
"""

import logging
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from arbiter.feedback.loop import OnlineLearner

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DEFAULT_PATH = _REPO_ROOT / "models" / "latency_predictor.pkl"


class RealTimeFeatureStore:
    """In-memory feature store with sliding window aggregations."""

    WINDOW_SIZE = 10
    COLD_START_THRESHOLD = 5

    def __init__(self):
        self.buffer = deque(maxlen=self.WINDOW_SIZE)

    def ingest(self, timestamp: int, load: float, latency: float) -> None:
        """Append new metric and maintain sliding window."""
        self.buffer.append(
            {
                "timestamp": timestamp,
                "current_load": float(load),
                "avg_latency_ms": float(latency),
            }
        )

    def get_features(self) -> Optional[List[float]]:
        """Compute features for model inference.

        Returns:
            list: [current_load, latency_ma_5, latency_slope] or None if cold start
        """
        if len(self.buffer) < self.COLD_START_THRESHOLD:
            return None

        latencies = [row["avg_latency_ms"] for row in self.buffer]
        current_load = self.buffer[-1]["current_load"]
        latency_ma_5 = float(np.mean(latencies[-5:]))
        latency_slope = float(latencies[-1] - latencies[-2]) if len(latencies) > 1 else 0.0

        return [current_load, latency_ma_5, latency_slope]


class IntelligentRouter:
    """ML-powered router with predictive circuit breaker.

    Uses a trained RandomForest as the primary predictor. When an OnlineLearner
    is provided and fitted, predictions are blended (70% RF / 30% online) so the
    feedback loop actively influences routing decisions.
    """

    LATENCY_THRESHOLD_MS = 300
    DECISION_PRIMARY = "PRIMARY"
    DECISION_REROUTE = "REROUTE"
    DECISION_ROUND_ROBIN = "ROUND_ROBIN"

    # Weight given to the online learner when blending predictions.
    ONLINE_BLEND_WEIGHT = 0.3

    def __init__(self, model_path, online_learner: Optional["OnlineLearner"] = None):
        """Load trained model.

        Args:
            model_path: Path to serialized RandomForest model file
            online_learner: Optional fitted OnlineLearner for blended prediction

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}. Run 'python -m arbiter.routing.model' first.")

        self.model = joblib.load(model_path)
        self.online_learner = online_learner
        logger.info(f"Loaded model from {model_path}")

    def decide(
        self,
        features: Optional[List[float]],
        online_learner: Optional["OnlineLearner"] = None,
    ) -> Tuple[Literal["PRIMARY", "REROUTE", "ROUND_ROBIN"], float]:
        """Make routing decision based on predicted latency.

        Args:
            features: Feature vector or None (cold start)
            online_learner: Override the instance-level learner for this call

        Returns:
            tuple: (decision_string, predicted_latency)
        """
        if features is None:
            return self.DECISION_ROUND_ROBIN, 0.0

        X = pd.DataFrame(
            [features],
            columns=["current_load", "latency_ma_5", "latency_slope"],
        )
        rf_pred = float(self.model.predict(X)[0])

        learner = online_learner or self.online_learner
        if learner is not None and learner.is_fitted:
            ol_pred = float(learner.predict(features)[0])
            predicted_latency = (1 - self.ONLINE_BLEND_WEIGHT) * rf_pred + self.ONLINE_BLEND_WEIGHT * ol_pred
        else:
            predicted_latency = rf_pred

        decision = self.DECISION_REROUTE if predicted_latency > self.LATENCY_THRESHOLD_MS else self.DECISION_PRIMARY
        return decision, predicted_latency


def simulate_live_traffic():
    """Simulate traffic spike scenario and demonstrate routing decisions."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Starting Arbiter routing engine...")

    store = RealTimeFeatureStore()
    try:
        router = IntelligentRouter(MODEL_DEFAULT_PATH)
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    logger.info("Connected to stream. Listening for metrics...")
    print("-" * 60)
    print(f"{'TIME':<10} | {'LOAD':<6} | {'ACTUAL LATENCY':<15} | {'DECISION':<25}")
    print("-" * 60)

    # Scenario: Normal → Spike → Recovery
    loads = [100] * 5 + [250] * 10 + [100] * 5

    for i, load in enumerate(loads):
        base_latency = 50 + (load * 0.8)

        if load > 200:
            base_latency += i * 20

        current_latency = base_latency + np.random.normal(0, 5)

        store.ingest(i, load, current_latency)
        features = store.get_features()
        decision, pred_val = router.decide(features)
        if decision == router.DECISION_REROUTE:
            decision_label = f"REROUTE (Pred: {pred_val:.0f}ms)"
        elif decision == router.DECISION_PRIMARY:
            decision_label = f"PRIMARY (Pred: {pred_val:.0f}ms)"
        else:
            decision_label = "ROUND_ROBIN (Cold Start)"

        print(f"T+{i}m       | {load:<6} | {current_latency:>6.1f} ms        | {decision_label}")
        time.sleep(0.2)


if __name__ == "__main__":
    simulate_live_traffic()
