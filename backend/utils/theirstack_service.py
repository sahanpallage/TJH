"""
TheirStack Job Search API Service.
Separate from JSearch and LinkedIn APIs.
Uses POST requests with Bearer token authentication.
"""
import logging
import time
from typing import Optional, List, Dict, Any

import requests

from settings import THEIRSTACK_API_KEY

logger = logging.getLogger(__name__)

# API Configuration
THEIRSTACK_API_URL = "https://api.theirstack.com/v1/jobs/search"
REQUEST_TIMEOUT_SECONDS = 15


def search_jobs_theirstack(
    page: int = 0,
    limit: int = 25,
    job_country_code_or: Optional[List[str]] = None,
    posted_at_max_age_days: Optional[int] = None,
    job_title_or: Optional[List[str]] = None,
    company_name_partial_match_or: Optional[List[str]] = None,
    job_location_pattern_or: Optional[List[str]] = None,
    remote: Optional[bool] = None,
    job_seniority_or: Optional[List[str]] = None,
    employment_statuses_or: Optional[List[str]] = None,
    min_salary_usd: Optional[int] = None,
    max_salary_usd: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search for jobs using TheirStack API.
    
    Args:
        page: Page number (default: 0)
        limit: Number of results per page (default: 25, max typically 100)
        job_country_code_or: List of country codes (e.g., ["US", "CA"])
        posted_at_max_age_days: Maximum age of job postings in days (e.g., 7 for past week)
        job_title_or: Natural language patterns to match job titles (case-insensitive)
        company_name_partial_match_or: Company names (case-insensitive partial match, e.g., "Google" matches "Google LLC")
        job_location_pattern_or: Regex patterns to match job locations (case-insensitive, searches city/state)
        remote: True for remote only, False for non-remote only, None for all
        job_seniority_or: List of seniority levels: ["c_level", "staff", "senior", "junior", "mid_level"]
        employment_statuses_or: List of employment types: ["full_time", "part_time"]
        min_salary_usd: Minimum annual salary in USD (e.g., 100000 for $100,000)
        max_salary_usd: Maximum annual salary in USD (e.g., 150000 for $150,000)
    
    Returns:
        List of job dictionaries
    """
    if not THEIRSTACK_API_KEY:
        raise ValueError("THEIRSTACK_API_KEY is not set in settings")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {THEIRSTACK_API_KEY}"
    }
    
    # Build request body
    json_body: Dict[str, Any] = {
        "page": page,
        "limit": limit
    }
    
    # Add optional parameters
    if job_country_code_or:
        json_body["job_country_code_or"] = job_country_code_or
    
    if posted_at_max_age_days is not None:
        json_body["posted_at_max_age_days"] = posted_at_max_age_days
    
    if job_title_or:
        json_body["job_title_or"] = job_title_or
    
    if company_name_partial_match_or:
        json_body["company_name_partial_match_or"] = company_name_partial_match_or
    
    if job_location_pattern_or:
        json_body["job_location_pattern_or"] = job_location_pattern_or
    
    if remote is not None:
        json_body["remote"] = remote
    
    if job_seniority_or:
        json_body["job_seniority_or"] = job_seniority_or
    
    if employment_statuses_or:
        json_body["employment_statuses_or"] = employment_statuses_or
    
    if min_salary_usd is not None:
        json_body["min_salary_usd"] = min_salary_usd
    
    if max_salary_usd is not None:
        json_body["max_salary_usd"] = max_salary_usd
    
    try:
        response = requests.post(
            THEIRSTACK_API_URL,
            headers=headers,
            json=json_body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        
        # Handle TheirStack API response structure: {metadata: {...}, data: [...]}
        if isinstance(data, dict):
            # Check metadata for counts
            if "metadata" in data:
                metadata = data.get("metadata", {})
                total = metadata.get("total", metadata.get("count", 0))
                page = metadata.get("page", metadata.get("current_page", 0))
                limit = metadata.get("limit", metadata.get("per_page", 0))
                logger.info(
                    "TheirStack metadata",
                    extra={"total": total, "page": page, "limit": limit},
                )
            
            # Extract jobs from data array
            if "data" in data:
                jobs = data["data"]
                if isinstance(jobs, list):
                    if len(jobs) == 0:
                        logger.info(
                            "TheirStack returned empty data array (no jobs match criteria)"
                        )
                    return jobs
                elif isinstance(jobs, dict):
                    # If data is a dict, check for nested arrays
                    if "items" in jobs:
                        return jobs["items"]
                    elif "jobs" in jobs:
                        return jobs["jobs"]
                    else:
                        logger.warning(
                            "'data' in TheirStack response is a dict with unexpected keys",
                            extra={"keys": list(jobs.keys())},
                        )
                        return []
                else:
                    return []
            # Fallback to other common keys
            elif "jobs" in data:
                return data["jobs"] if isinstance(data["jobs"], list) else []
            elif "results" in data:
                return data["results"] if isinstance(data["results"], list) else []
            elif "items" in data:
                return data["items"] if isinstance(data["items"], list) else []
            else:
                logger.warning(
                    "Unknown TheirStack response structure",
                    extra={"keys": list(data.keys())},
                )
                return []
        elif isinstance(data, list):
            # Direct list response
            return data
        else:
            return []
            
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if getattr(e, "response", None) else None
        logger.error(
            "Error fetching jobs from TheirStack",
            extra={
                "error": str(e),
                "status_code": status_code,
            },
        )
        raise
    except requests.RequestException as e:
        logger.error("Unexpected requests error calling TheirStack", extra={"error": str(e)})
        raise


def search_jobs_theirstack_multiple_pages(
    num_pages: int = 1,
    limit: int = 25,
    job_country_code_or: Optional[List[str]] = None,
    posted_at_max_age_days: Optional[int] = None,
    job_title_or: Optional[List[str]] = None,
    company_name_partial_match_or: Optional[List[str]] = None,
    job_location_pattern_or: Optional[List[str]] = None,
    remote: Optional[bool] = None,
    job_seniority_or: Optional[List[str]] = None,
    employment_statuses_or: Optional[List[str]] = None,
    min_salary_usd: Optional[int] = None,
    max_salary_usd: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search for jobs across multiple pages using TheirStack API.
    
    Args:
        num_pages: Number of pages to fetch (default: 1)
        limit: Number of results per page
        Other parameters same as search_jobs_theirstack
    
    Returns:
        List of all jobs from all pages
    """
    all_jobs: List[Dict[str, Any]] = []
    
    print(f"Searching TheirStack jobs...")
    if job_title_or:
        print(f"  Job Title Patterns: {', '.join(job_title_or)}")
    if company_name_partial_match_or:
        print(f"  Company Names: {', '.join(company_name_partial_match_or)}")
    if job_country_code_or:
        print(f"  Countries: {', '.join(job_country_code_or)}")
    if job_location_pattern_or:
        print(f"  Location Patterns: {', '.join(job_location_pattern_or)}")
    if posted_at_max_age_days:
        print(f"  Posted within: {posted_at_max_age_days} days")
    if remote is not None:
        print(f"  Remote: {'Yes' if remote else 'No'}")
    if job_seniority_or:
        print(f"  Seniority: {', '.join(job_seniority_or)}")
    if employment_statuses_or:
        print(f"  Employment Types: {', '.join(employment_statuses_or)}")
    print(f"Fetching {num_pages} page(s) with {limit} jobs per page...")
    
    for page in range(num_pages):
        try:
            # Add delay between pages to avoid rate limiting
            if page > 0:
                delay = 1.0  # 1 second between pages
                print(f"Waiting {delay} seconds before fetching page {page + 1}...")
                time.sleep(delay)
            
            jobs = search_jobs_theirstack(
                page=page,
                limit=limit,
                job_country_code_or=job_country_code_or,
                posted_at_max_age_days=posted_at_max_age_days,
                job_title_or=job_title_or,
                company_name_partial_match_or=company_name_partial_match_or,
                job_location_pattern_or=job_location_pattern_or,
                remote=remote,
                job_seniority_or=job_seniority_or,
                employment_statuses_or=employment_statuses_or,
                min_salary_usd=min_salary_usd,
                max_salary_usd=max_salary_usd
            )
            
            if jobs:
                print(f"Page {page + 1}: Found {len(jobs)} jobs")
                all_jobs.extend(jobs)
            else:
                print(f"Page {page + 1}: No jobs found")
                # If no jobs on a page and we're on page 0, stop immediately to save credits
                if page == 0:
                    print("💡 Stopping after first page to save API credits")
                    break
                # If no jobs on later pages, likely no more pages available
                break
                
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                print(f"⚠️  Rate limit hit on page {page + 1}. Stopping to avoid further rate limits.")
                print("💡 Tip: Wait a few minutes before running again, or reduce the number of pages.")
                break
            elif e.response and e.response.status_code == 401:
                print(f"❌ Unauthorized (401) on page {page + 1}. Check your THEIRSTACK_API_KEY.")
                break
            else:
                print(f"Error fetching page {page + 1}: {e}")
                # Continue to next page for other errors
                continue
        except Exception as e:
            print(f"Error fetching page {page + 1}: {e}")
            # Continue to next page instead of failing completely
            continue
    
    print(f"Total jobs found: {len(all_jobs)}")
    return all_jobs


def normalize_theirstack_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize TheirStack job data to a consistent format.
    
    Args:
        job: Raw job dictionary from API
    
    Returns:
        Normalized job dictionary
    """
    # Map common field names to standard format
    normalized = {
        "job_id": job.get("job_id") or job.get("id") or job.get("jobId") or "",
        "title": job.get("title") or job.get("job_title") or job.get("jobTitle") or "",
        "company": job.get("company") or job.get("company_name") or job.get("companyName") or job.get("employer_name") or "",
        "location": job.get("location") or job.get("job_location") or job.get("jobLocation") or "",
        "city": job.get("city") or job.get("job_city") or "",
        "state": job.get("state") or job.get("job_state") or job.get("state_code") or "",
        "country": job.get("country") or job.get("job_country") or "",
        "link": job.get("link") or job.get("url") or job.get("job_url") or job.get("jobUrl") or job.get("apply_link") or job.get("applyLink") or "",
        "date_posted": job.get("date_posted") or job.get("postedAt") or job.get("posted_at") or job.get("postedAt") or "",
        "description": job.get("description") or job.get("job_description") or job.get("jobDescription") or "",
        "employment_type": job.get("employment_type") or job.get("employmentType") or job.get("employment_status") or (", ".join(job.get("employment_statuses", [])) if isinstance(job.get("employment_statuses"), list) else "") or job.get("job_employment_type") or job.get("jobEmploymentType") or "",
        "remote": job.get("remote") or job.get("remote_type") or job.get("is_remote") or "",
        "salary": job.get("salary") or job.get("salary_range") or "",
    }
    
    return normalized

