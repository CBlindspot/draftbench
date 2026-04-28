"""USPTO patent-number verification — backbone of the Therasense kill-switch.

For each cited patent number in a draft, we need to answer: does this patent
exist in the USPTO record? Class A hallucinations (Therasense kill-switch)
are fabricated patent numbers — citations that look real but don't.

Verification chain (first available source wins):

  1. PatentsView API (`PATENTSVIEW_API_KEY` env var, free tier with rate limit)
     — official USPTO bulk-data project, JSON REST.
  2. Google Patents probe (no auth) — HTTP HEAD on
     `https://patents.google.com/patent/US{number}`. 200 = exists, 404 = not.
     Subject to rate limits and is the fragile fallback.
  3. If neither source is reachable, return `None` ("unverified") rather than
     a false negative — Therasense is too consequential to guess on.

Verifications are cached on disk under `~/.cache/draftbench/uspto/{number}.json`
(override with `cache_dir=`). Cache entries never expire by default — patent
numbers don't change.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

VerificationSource = Literal["patentsview", "google_patents", "cache", "unverified"]


@dataclass
class VerificationResult:
    patent_number: str
    exists: bool | None  # True = exists, False = confirmed not exist, None = unverified
    source: VerificationSource
    detail: str = ""


class USPTOClient:
    """Verifies US patent numbers against PatentsView, with a Google Patents fallback."""

    PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"
    GOOGLE_PATENTS_URL = "https://patents.google.com/patent/US{number}"

    def __init__(
        self,
        patentsview_api_key: str | None = None,
        cache_dir: str | Path | None = None,
        timeout: float = 10.0,
        google_fallback: bool = True,
    ):
        self.patentsview_api_key = patentsview_api_key or os.environ.get("PATENTSVIEW_API_KEY")
        self.cache_dir = (
            Path(cache_dir) if cache_dir else Path.home() / ".cache" / "draftbench" / "uspto"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.google_fallback = google_fallback
        self._memory_cache: dict[str, VerificationResult] = {}
        self._client: httpx.Client | None = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # --------------------------------------------------------------------- API

    def verify(self, patent_number: str) -> VerificationResult:
        """Verify a single patent number. Caches both confirmed-exist and confirmed-not-exist."""
        normalized = _normalize_number(patent_number)
        if not normalized:
            return VerificationResult(
                patent_number=patent_number,
                exists=None,
                source="unverified",
                detail="Could not normalize patent number",
            )

        if normalized in self._memory_cache:
            return self._memory_cache[normalized]

        cache_file = self.cache_dir / f"{normalized}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                result = VerificationResult(
                    patent_number=normalized,
                    exists=data.get("exists"),
                    source="cache",
                    detail=data.get("detail", ""),
                )
                self._memory_cache[normalized] = result
                return result
            except (json.JSONDecodeError, OSError):
                pass

        result = self._lookup(normalized)
        self._memory_cache[normalized] = result
        # Only persist confirmed verdicts — don't cache "unverified" outcomes,
        # so a transient API outage doesn't poison subsequent runs.
        if result.exists is not None:
            try:
                cache_file.write_text(
                    json.dumps(
                        {"exists": result.exists, "source": result.source, "detail": result.detail}
                    )
                )
            except OSError:
                pass
        return result

    def verify_many(self, patent_numbers: list[str]) -> list[VerificationResult]:
        return [self.verify(n) for n in patent_numbers]

    # ---------------------------------------------------------------- helpers

    def _lookup(self, normalized: str) -> VerificationResult:
        if self.patentsview_api_key:
            r = self._lookup_patentsview(normalized)
            if r.exists is not None:
                return r
        if self.google_fallback:
            return self._lookup_google_patents(normalized)
        return VerificationResult(
            patent_number=normalized,
            exists=None,
            source="unverified",
            detail="No verification source available",
        )

    def _lookup_patentsview(self, normalized: str) -> VerificationResult:
        try:
            response = self._http().post(
                self.PATENTSVIEW_URL,
                headers={
                    "X-Api-Key": self.patentsview_api_key or "",
                    "Content-Type": "application/json",
                },
                json={
                    "q": {"patent_id": normalized},
                    "f": ["patent_id"],
                    "o": {"size": 1},
                },
            )
            if response.status_code == 200:
                data = response.json()
                patents = data.get("patents") or []
                exists = bool(patents) and any(
                    p.get("patent_id") == normalized for p in patents
                )
                return VerificationResult(
                    patent_number=normalized,
                    exists=exists,
                    source="patentsview",
                    detail=f"PatentsView returned {len(patents)} record(s)",
                )
            return VerificationResult(
                patent_number=normalized,
                exists=None,
                source="unverified",
                detail=f"PatentsView HTTP {response.status_code}",
            )
        except (httpx.RequestError, httpx.HTTPError) as exc:
            return VerificationResult(
                patent_number=normalized,
                exists=None,
                source="unverified",
                detail=f"PatentsView request error: {exc}",
            )

    def _lookup_google_patents(self, normalized: str) -> VerificationResult:
        url = self.GOOGLE_PATENTS_URL.format(number=normalized)
        try:
            response = self._http().head(url)
            if response.status_code == 200:
                return VerificationResult(
                    patent_number=normalized,
                    exists=True,
                    source="google_patents",
                    detail=f"HEAD {url} → 200",
                )
            if response.status_code == 404:
                return VerificationResult(
                    patent_number=normalized,
                    exists=False,
                    source="google_patents",
                    detail=f"HEAD {url} → 404",
                )
            return VerificationResult(
                patent_number=normalized,
                exists=None,
                source="unverified",
                detail=f"Google Patents HTTP {response.status_code}",
            )
        except (httpx.RequestError, httpx.HTTPError) as exc:
            return VerificationResult(
                patent_number=normalized,
                exists=None,
                source="unverified",
                detail=f"Google Patents request error: {exc}",
            )


_PATENT_DIGITS_RE = re.compile(r"(\d{1,2}[,\.\s]?\d{3}[,\.\s]?\d{3})")


def _normalize_number(raw: str) -> str:
    """Extract the canonical digit-only patent number from a raw citation string.

    Handles "US 9,123,456 B2" → "9123456" by matching the 7-8-digit pattern
    explicitly rather than greedily stripping all non-digits (which would
    incorrectly absorb the "2" from the "B2" kind code).

    Returns an empty string if no plausible patent-number pattern is found.
    """
    m = _PATENT_DIGITS_RE.search(raw)
    if not m:
        return ""
    return "".join(ch for ch in m.group(1) if ch.isdigit())


# ----------------------------------------------------------------- rate-limit

def polite_sleep(seconds: float = 0.2) -> None:
    """Tiny delay between bulk requests to avoid tripping rate limits."""
    time.sleep(seconds)
