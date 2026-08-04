"""
Structured logging for the applied AI recommender pipeline.

Every step of the agent (plan, recommend, critique, refine) emits a JSON
record. The same log stream drives both the human-readable terminal trace
and the machine-parseable evaluation report used by the reliability harness.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent_run.jsonl")


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _build_stdlib_logger() -> logging.Logger:
    logger = logging.getLogger("vibematch")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


_stdlib_logger = _build_stdlib_logger()


@dataclass
class RunLog:
    """
    Collects the structured events for a single agent invocation and can
    write them to a JSONL file at the end. Kept in-memory so tests can
    assert on the trace without touching disk.
    """
    run_id: str
    events: List[Dict[str, Any]] = field(default_factory=list)

    def event(self, step: str, level: str = "info", **payload: Any) -> None:
        record = {"run_id": self.run_id, "step": step, "level": level, **payload}
        self.events.append(record)
        msg = f"[{self.run_id}] {step}: " + ", ".join(f"{k}={v}" for k, v in payload.items())
        if level == "warn":
            _stdlib_logger.warning(msg)
        elif level == "error":
            _stdlib_logger.error(msg)
        else:
            _stdlib_logger.info(msg)

    def flush_to_disk(self, path: Optional[str] = None) -> str:
        _ensure_log_dir()
        target = path or LOG_FILE
        with open(target, "a", encoding="utf-8") as f:
            for record in self.events:
                f.write(json.dumps(record) + "\n")
        return target

    def steps(self) -> List[str]:
        return [e["step"] for e in self.events]

    def find(self, step: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e["step"] == step]
