"""
Simple cache service for job search results backed by Supabase Postgres.

We use Supabase's REST API to store and retrieve cached responses for
repeated queries so we don't keep hitting external APIs (JSearch / Indeed / LinkedIn)
with identical parameters.

Expected Supabase table (create this in your Supabase project):

  CREATE TABLE job_cache (
    service    text    NOT NULL,
    cache_key  text    NOT NULL,
    response   jsonb   NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (service, cache_key)
  );

  CREATE INDEX idx_job_cache_created_at ON job_cache(created_at);
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Dict, Optional, Tuple

import requests

from settings import SUPABASE_URL, SUPABASE_KEY


logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
  service: str
  key: str
  data: Dict[str, Any]
  created_at: datetime


# Default cache TTL: 7 days (in minutes)
CACHE_TTL_MINUTES = 60 * 24 * 7

class JobCache:
  """
  Very small, focused cache for job search responses using Supabase.

  Table schema (job_cache):
    service     text   (e.g., 'jsearch', 'indeed', 'linkedin')
    cache_key   text   (hash of normalized request)
    response    jsonb  (JobSearchResponse payload)
    created_at  timestamptz
  """

  def __init__(self) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
      # If Supabase is not configured, we behave like a no-op cache
      logger.warning("Supabase URL / KEY not set; JobCache will be disabled.")
      self.enabled = False
    else:
      self.enabled = True
      self.base_url = SUPABASE_URL.rstrip("/") + "/rest/v1/job_cache"
      self.headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
      }

  @staticmethod
  def _compute_key(service: str, payload: Dict[str, Any]) -> str:
    # Normalize JSON payload so equivalent bodies hash to same key
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(f"{service}:{normalized}".encode("utf-8")).hexdigest()

  def get(
    self, service: str, payload: Dict[str, Any], ttl_minutes: int = CACHE_TTL_MINUTES
  ) -> Tuple[Optional[CacheResult], bool]:
    """
    Return (CacheResult or None, hit:boolean).
    """
    if not self.enabled:
      return None, False

    key = self._compute_key(service, payload)
    # Use timezone-aware UTC datetimes to avoid naive/aware comparison errors
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)

    params = {
      "select": "response,created_at",
      "service": f"eq.{service}",
      "cache_key": f"eq.{key}",
      "order": "created_at.desc",
      "limit": "1",
    }

    try:
      resp = requests.get(
        self.base_url,
        headers=self.headers,
        params=params,
        timeout=5,  # Add timeout to prevent hanging
      )
      resp.raise_for_status()
      rows = resp.json()
    except requests.RequestException as e:
      logger.warning("Cache get failed", extra={"error": str(e), "service": service})
      return None, False

    if not rows:
      return None, False

    row = rows[0]
    response_data = row.get("response")
    created_at_str = row.get("created_at")

    if not response_data or not created_at_str:
      return None, False

    try:
      created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
      if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    except Exception:
      return None, False

    if created_at < cutoff:
      # Expired; treat as miss
      return None, False

    return CacheResult(service=service, key=key, data=response_data, created_at=created_at), True

  def set(self, service: str, payload: Dict[str, Any], response: Dict[str, Any]) -> None:
    if not self.enabled:
      return

    key = self._compute_key(service, payload)
    created_at = datetime.utcnow().isoformat()

    body = [
      {
        "service": service,
        "cache_key": key,
        "response": response,
        "created_at": created_at,
      }
    ]

    params = {"on_conflict": "service,cache_key"}

    try:
      resp = requests.post(
        self.base_url,
        headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
        params=params,
        json=body,
        timeout=5,
      )
      resp.raise_for_status()
    except requests.RequestException as e:
      logger.warning(
        "Cache set failed",
        extra={
          "error": str(e),
          "service": service,
        },
      )
      return

