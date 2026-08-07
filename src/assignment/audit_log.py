"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, dict] = {}
        self._counter = 0

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """Store input + start timestamp keyed by request_id/user_id."""
        self._counter += 1
        request_id = request_id or f"{user_id}-{self._counter}"
        self._open[request_id] = {
            "input": text,
            "start_ts": time.time(),
            "start_time": utc_now_iso(),
        }
        return request_id

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ):
        """Store output, layer decision, latency; append to self.logs."""
        opened = self._open.pop(request_id, None) if request_id else None
        latency_ms = (
            (time.time() - opened["start_ts"]) * 1000 if opened else None
        )
        entry = {
            "request_id": request_id,
            "user_id": user_id,
            "input": opened["input"] if opened else None,
            "output": text,
            "blocked": blocked,
            "layer": layer,
            "timestamp": utc_now_iso(),
            "latency_ms": latency_ms,
        }
        self.logs.append(entry)
        return entry

    def export_json(self, filepath: str = "outputs/audit_log.json"):
        """Write logs to disk (JSON array)."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
