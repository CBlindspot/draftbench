"""USPTOClient — caching, normalization, and source-fallback logic.

External HTTP is mocked; the real PatentsView and Google Patents endpoints are
not contacted from the test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from draftbench.uspto import USPTOClient, _normalize_number


def test_normalize_strips_non_digits() -> None:
    assert _normalize_number("US 9,123,456 B2") == "9123456"
    assert _normalize_number("U.S. Pat. No. 10,234,567") == "10234567"
    assert _normalize_number("9.123.456") == "9123456"


def test_normalize_returns_empty_for_no_digits() -> None:
    assert _normalize_number("not a number") == ""


def test_unverified_when_no_sources(tmp_path: Path) -> None:
    client = USPTOClient(
        patentsview_api_key=None, cache_dir=tmp_path, google_fallback=False
    )
    result = client.verify("9,123,456")
    assert result.exists is None
    assert result.source == "unverified"


def test_disk_cache_round_trip(tmp_path: Path) -> None:
    """Verdict written to disk on first call, read on second without HTTP."""
    client = USPTOClient(
        patentsview_api_key=None, cache_dir=tmp_path, google_fallback=True
    )

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_http = MagicMock()
    fake_http.head.return_value = fake_response
    client._client = fake_http  # inject

    r1 = client.verify("9,123,456")
    assert r1.exists is True
    assert r1.source == "google_patents"
    assert fake_http.head.call_count == 1

    # Drop the in-memory cache to force a disk-read path
    client._memory_cache.clear()
    fake_http.head.reset_mock()

    r2 = client.verify("9,123,456")
    assert r2.exists is True
    assert r2.source == "cache"
    assert fake_http.head.call_count == 0  # served from disk


def test_unverified_does_not_get_cached(tmp_path: Path) -> None:
    """Transient failures (None) must not persist to disk."""
    client = USPTOClient(
        patentsview_api_key=None, cache_dir=tmp_path, google_fallback=False
    )
    r = client.verify("9,123,456")
    assert r.exists is None
    cache_files = list(tmp_path.glob("*.json"))
    assert cache_files == []


def test_google_404_caches_negative(tmp_path: Path) -> None:
    """Confirmed-not-exist (404) is a real verdict and is cached."""
    client = USPTOClient(
        patentsview_api_key=None, cache_dir=tmp_path, google_fallback=True
    )
    fake_response = MagicMock()
    fake_response.status_code = 404
    fake_http = MagicMock()
    fake_http.head.return_value = fake_response
    client._client = fake_http

    r = client.verify("99,999,999")
    assert r.exists is False
    assert r.source == "google_patents"
    assert (tmp_path / "99999999.json").exists()


def test_patentsview_short_circuits_google(tmp_path: Path) -> None:
    """PatentsView verdict is sufficient — Google fallback should not be called."""
    client = USPTOClient(
        patentsview_api_key="test-key", cache_dir=tmp_path, google_fallback=True
    )
    fake_pv_response = MagicMock()
    fake_pv_response.status_code = 200
    fake_pv_response.json.return_value = {
        "patents": [{"patent_id": "9123456"}]
    }
    fake_http = MagicMock()
    fake_http.post.return_value = fake_pv_response
    fake_http.head.side_effect = AssertionError("Google fallback should not run")
    client._client = fake_http

    r = client.verify("9,123,456")
    assert r.exists is True
    assert r.source == "patentsview"
    assert fake_http.head.called is False


def test_patentsview_failure_falls_through_to_google(tmp_path: Path) -> None:
    """PatentsView 5xx → fall back to Google Patents."""
    client = USPTOClient(
        patentsview_api_key="test-key", cache_dir=tmp_path, google_fallback=True
    )
    fake_pv_response = MagicMock()
    fake_pv_response.status_code = 503
    fake_g_response = MagicMock()
    fake_g_response.status_code = 200
    fake_http = MagicMock()
    fake_http.post.return_value = fake_pv_response
    fake_http.head.return_value = fake_g_response
    client._client = fake_http

    r = client.verify("9,123,456")
    assert r.exists is True
    assert r.source == "google_patents"


def test_empty_normalization_returns_unverified(tmp_path: Path) -> None:
    client = USPTOClient(cache_dir=tmp_path)
    r = client.verify("not a number")
    assert r.exists is None
    assert r.source == "unverified"
