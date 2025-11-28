import logging
import math
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from jobspy import scrape_jobs

logger = logging.getLogger(__name__)


def _map_hours_old(date_posted: Optional[str]) -> Optional[int]:
    """
    Map the frontend "Freshness" dropdown into JobSpy's hours_old parameter.
    """
    if not date_posted:
        return None

    value = date_posted.lower()
    if "day" in value or "today" in value:
        return 24
    if "week" in value:
        return 24 * 7
    if "month" in value:
        return 24 * 30
    return None


def search_linkedin_jobs(
    job_title: str,
    industry: str = "",
    city: str = "",
    country: str = "",
    date_posted: str = "",
    results_wanted: int = 20,
) -> List[Dict[str, Any]]:
    """
    Use JobSpy to scrape LinkedIn jobs and return a list of JobPost-like dicts.

    This mirrors the JobSpy usage described in the README:
    https://github.com/speedyapply/JobSpy
    """
    # Build search_term: favour explicit job title and optionally industry
    query_parts: List[str] = []
    if job_title:
        query_parts.append(job_title)
    if industry:
        query_parts.append(industry)
    search_term = " ".join(query_parts) if query_parts else job_title

    # LinkedIn uses only the location string, no explicit country param
    location_parts: List[str] = []
    if city:
        location_parts.append(city)
    if country:
        location_parts.append(country)
    location = ", ".join(location_parts) if location_parts else ""

    hours_old = _map_hours_old(date_posted)

    logger.info(
        "Searching LinkedIn via JobSpy",
        extra={
            "search_term": search_term,
            "location": location,
            "hours_old": hours_old,
            "results_wanted": results_wanted,
        },
    )

    jobs_df = scrape_jobs(
        site_name=["linkedin"],
        search_term=search_term,
        location=location or None,
        results_wanted=results_wanted,
        hours_old=hours_old,
        linkedin_fetch_description=True,
        verbose=1,
    )

    # JobSpy returns a pandas DataFrame – convert to list of dicts
    # and normalise the important fields we care about.
    records: List[Dict[str, Any]] = jobs_df.to_dict(orient="records")  # type: ignore[no-untyped-call]

    normalized: List[Dict[str, Any]] = []
    for job in records:
        # Column names are based on JobSpy's documented JobPost schema.
        city_val = job.get("city") or ""
        state_val = job.get("state") or ""
        country_val = job.get("country") or ""

        location_tokens = [t for t in [city_val, state_val, country_val] if t]
        location_str = ", ".join(location_tokens) or job.get("location", "") or ""

        interval = (job.get("interval") or "")  # yearly, hourly, etc.
        min_amount = job.get("min_amount")
        max_amount = job.get("max_amount")
        currency = job.get("currency") or ""

        def _to_int_str(val: Any) -> str:
            """Convert numeric value to int string, safely handling NaN."""
            if not isinstance(val, (int, float)):
                return ""
            try:
                if isinstance(val, float) and math.isnan(val):
                    return ""
            except TypeError:
                return ""
            return str(int(val))

        salary_str = ""
        if min_amount is not None or max_amount is not None:
            low = _to_int_str(min_amount)
            high = _to_int_str(max_amount)
            if low and high:
                salary_str = f"{currency} {low} - {high} {interval}".strip()
            elif low:
                salary_str = f"{currency} {low}+ {interval}".strip()
            elif high:
                salary_str = f"Up to {currency} {high} {interval}".strip()

        posted_raw = job.get("date_posted", "") or ""
        if isinstance(posted_raw, (date, datetime)):
            posted_str = posted_raw.isoformat()
        else:
            posted_str = str(posted_raw) if posted_raw else ""

        normalized.append(
            {
                "id": str(job.get("job_url") or job.get("id") or job.get("title") or ""),
                "title": job.get("title", "") or "",
                "company": job.get("company", "") or "",
                "location": location_str,
                "city": city_val,
                "state": state_val,
                "country": country_val,
                "salary": salary_str,
                "type": job.get("job_type", "") or "",
                "remote": bool(job.get("is_remote", False)),
                "posted": posted_str,
                "description": (job.get("description") or "")[:500],
                "applyLink": job.get("job_url", "") or "",
            }
        )

    return normalized


