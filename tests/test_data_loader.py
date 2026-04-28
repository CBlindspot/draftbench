"""DataLoader JSONL reading + filters."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from draftbench.data_loader import DataLoader


@pytest.fixture()
def tmp_jsonl(tmp_path: Path) -> Path:
    p = tmp_path / "cases.jsonl"
    records = [
        {
            "id": "alpha",
            "title": "Alpha",
            "domain": "mechanical",
            "tier": 1,
            "background": "bg",
            "inventive_elements": ["one", "two"],
            "embodiments": "emb",
        },
        {
            "id": "beta",
            "title": "Beta",
            "domain": "software",
            "tier": 3,
            "background": "bg",
            "inventive_elements": ["one"],
            "embodiments": "emb",
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


def test_load_file(tmp_jsonl: Path) -> None:
    records = DataLoader(tmp_jsonl.parent).load_file(tmp_jsonl)
    assert len(records) == 2
    assert records[0]["id"] == "alpha"
    assert records[1]["domain"] == "software"


def test_filter_by_domain(tmp_jsonl: Path) -> None:
    loader = DataLoader(tmp_jsonl.parent)
    records = loader.load_file(tmp_jsonl)
    out = loader.filter(records, domain="mechanical")
    assert [r["id"] for r in out] == ["alpha"]


def test_filter_by_tier(tmp_jsonl: Path) -> None:
    loader = DataLoader(tmp_jsonl.parent)
    records = loader.load_file(tmp_jsonl)
    out = loader.filter(records, tier=3)
    assert [r["id"] for r in out] == ["beta"]


def test_validation_rejects_missing_field(tmp_path: Path) -> None:
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps({"id": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required fields"):
        DataLoader(tmp_path).load_file(p)


def test_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    p = tmp_path / "cases.jsonl"
    record = {
        "id": "alpha", "title": "A", "domain": "mechanical",
        "background": "b", "inventive_elements": ["x"], "embodiments": "e",
    }
    p.write_text(textwrap.dedent(f"""\
        # comment line
        {json.dumps(record)}

        # another comment
    """), encoding="utf-8")
    records = DataLoader(tmp_path).load_file(p)
    assert len(records) == 1
