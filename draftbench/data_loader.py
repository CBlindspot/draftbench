"""Load invention test cases from JSONL files.

Expected schema per record:

    {
        "id": "snake_case_id",
        "title": "Title of the Invention",
        "domain": "mechanical | medtech | software | chemistry | biotech | ...",
        "tier": 1-5,
        "background": "...",
        "inventive_elements": ["...", "..."],
        "embodiments": "...",
        "prior_art_summary": "..."   # optional
    }
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

REQUIRED_FIELDS = ("id", "title", "domain", "background", "inventive_elements", "embodiments")


class DataLoader:
    """Load invention records from JSONL test sets."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def load_file(self, path: str | Path) -> list[dict]:
        """Load a single JSONL file. Each line is one invention record."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        records: list[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{lineno} invalid JSON: {exc}") from exc
                self._validate(record, source=f"{path}:{lineno}")
                records.append(record)
        return records

    def load_all(self, pattern: str = "*.jsonl") -> list[dict]:
        """Load every JSONL file under `data_dir` matching `pattern`."""
        records: list[dict] = []
        for fp in sorted(self.data_dir.rglob(pattern)):
            records.extend(self.load_file(fp))
        return records

    def filter(
        self,
        records: Iterable[dict],
        *,
        domain: str | None = None,
        tier: int | None = None,
        ids: list[str] | None = None,
    ) -> list[dict]:
        """Apply optional filters."""
        out = []
        ids_set = set(ids) if ids else None
        for r in records:
            if domain and r.get("domain") != domain:
                continue
            if tier is not None and r.get("tier") != tier:
                continue
            if ids_set is not None and r.get("id") not in ids_set:
                continue
            out.append(r)
        return out

    @staticmethod
    def _validate(record: dict, source: str) -> None:
        missing = [f for f in REQUIRED_FIELDS if f not in record]
        if missing:
            raise ValueError(f"{source} missing required fields: {missing}")
        if not isinstance(record["inventive_elements"], list):
            raise ValueError(f"{source} `inventive_elements` must be a list")
