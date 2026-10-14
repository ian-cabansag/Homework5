"""Append-only operational audit journal stored as newline-delimited JSON."""

import asyncio
import json
from pathlib import Path
from typing import Any

from backend.models import AgentEvent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"


class AuditTrail:
    def __init__(self, path: Path = AUDIT_PATH) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def append(self, event: AgentEvent) -> None:
        """Append one complete event line; existing audit records are never rewritten."""
        encoded = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as journal:
                journal.write(encoded + "\n")
                journal.flush()

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as journal:
            for line in journal:
                if line.strip():
                    result.append(json.loads(line))
        return result

    def pending_approval(self, approval_id: str) -> dict[str, Any] | None:
        return next((event for event in self.pending_approvals()
                     if event.get("approval_id") == approval_id), None)

    def current_events(self) -> list[dict[str, Any]]:
        """Current database generation; previous generations remain in the journal."""
        events = self.events()
        start = 0
        for index, event in enumerate(events):
            if event.get("event_type") == "working_database_reset":
                start = index + 1
        return events[start:]

    def pending_approvals(self) -> list[dict[str, Any]]:
        outstanding: dict[str, dict[str, Any]] = {}
        for event in self.current_events():
            approval_id = event.get("approval_id")
            if not approval_id:
                continue
            if event.get("event_type") == "approval_requested":
                outstanding[approval_id] = event
            elif event.get("event_type") in {"approval_decision", "payment_executed", "payment_blocked"}:
                outstanding.pop(approval_id, None)
        return list(outstanding.values())
