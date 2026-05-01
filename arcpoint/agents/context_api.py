"""Context API for exposing real-time system state to the routing agent.

Provides structured access to:
- Model health and performance metrics
- Backend availability and load
- Recent incident history
- Traffic patterns

When the Context Service (FastAPI on localhost:8000) is reachable, data is
fetched from it directly so the agent always sees the same state as the API.
If the service is unavailable, the class falls back to embedded mock data so
the agent can still run in isolation (e.g. during tests or local development
without the server started).
"""

import logging
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    """Health status of an AI model."""

    model_id: str
    availability: str  # "available", "degraded", "down"
    error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    requests_per_min: int


@dataclass
class BackendStatus:
    """Current state of a compute backend."""

    backend_id: str
    region: str
    provider: str
    current_load: int
    capacity: int
    spot_available: bool
    cost_per_request: float


@dataclass
class Incident:
    """Recent system incident."""

    timestamp: str
    severity: str
    affected_service: str
    description: str


class ContextAPI:
    """API for querying system context in real-time.

    Tries the REST Context Service first; falls back to embedded mock data.

    Args:
        base_url: Base URL of the running Context Service.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def _try_get(self, path: str, params: Optional[Dict] = None) -> Optional[object]:
        """Attempt a GET against the REST service; return parsed JSON or None."""
        try:
            import requests

            resp = requests.get(f"{self.base_url}{path}", params=params, timeout=1)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Public interface — returns plain dicts so callers stay schema-agnostic
    # ------------------------------------------------------------------

    def get_model_health(self, model_id: Optional[str] = None) -> List[Dict]:
        """Get health status of models."""
        params = {"model_id": model_id} if model_id else None
        result = self._try_get("/models", params)
        if result is not None:
            return result

        models = [
            ModelHealth("gpt-4-turbo", "available", 0.02, 450, 1200, 1200),
            ModelHealth("claude-3-opus", "degraded", 0.15, 850, 2100, 450),
            ModelHealth("llama-3-70b", "available", 0.01, 200, 450, 800),
        ]
        if model_id:
            models = [m for m in models if m.model_id == model_id]
        return [asdict(m) for m in models]

    def get_backend_status(self) -> List[Dict]:
        """Get current status of all compute backends."""
        result = self._try_get("/backends")
        if result is not None:
            return result

        backends = [
            BackendStatus("aws-us-east-1", "us-east-1", "AWS", 750, 1000, True, 0.008),
            BackendStatus("gcp-us-central1", "us-central1", "GCP", 200, 800, False, 0.012),
            BackendStatus("azure-eastus", "eastus", "Azure", 450, 600, True, 0.010),
        ]
        return [asdict(b) for b in backends]

    def get_recent_incidents(self, hours: int = 24) -> List[Dict]:
        """Get incidents from the last N hours."""
        result = self._try_get("/incidents", {"hours": hours})
        if result is not None:
            return result

        now = datetime.now()
        incidents = [
            Incident(
                timestamp=(now - timedelta(hours=2)).isoformat(),
                severity="warning",
                affected_service="claude-3-opus",
                description="Elevated latency on Claude models due to upstream API rate limits",
            ),
            Incident(
                timestamp=(now - timedelta(hours=8)).isoformat(),
                severity="critical",
                affected_service="aws-us-east-1",
                description="AWS availability zone outage caused 5-minute downtime",
            ),
        ]
        return [asdict(i) for i in incidents]

    def get_user_context(self, user_id: str) -> Dict:
        """Get user-specific context (SLA, tier, quotas)."""
        result = self._try_get(f"/users/{user_id}")
        if result is not None:
            return result

        tier = "standard"
        lowered = user_id.lower()
        if "premium" in lowered or "pro" in lowered:
            tier = "premium"
        elif "free" in lowered:
            tier = "free"

        return {
            "user_id": user_id,
            "tier": tier,
            "sla_latency_ms": 500,
            "monthly_quota": 1000000,
            "quota_used": 750000,
            "cost_ceiling_per_request": 0.015,
            "prefers_cost_optimization": False,
        }

    def get_traffic_forecast(self, minutes_ahead: int = 60) -> Dict:
        """Get predicted traffic for the next N minutes."""
        result = self._try_get("/forecast", {"minutes_ahead": minutes_ahead})
        if result is not None:
            return result

        current_rpm = 2500
        delta = random.randint(-200, 800)
        predicted_rpm = current_rpm + delta

        if delta > 100:
            trend = "up"
        elif delta < -100:
            trend = "down"
        else:
            trend = "stable"

        return {
            "current_requests_per_min": current_rpm,
            "predicted_requests_per_min": predicted_rpm,
            "confidence": 0.85,
            "trend": trend,
        }
