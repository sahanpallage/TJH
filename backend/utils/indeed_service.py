"""
Indeed Job Scraper Service using Apify API.
Based on the implementation in "Indeed scrapper" folder.
Uses Apify's Indeed scraper actor which handles Cloudflare and other protections.
"""
import logging
import time
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import requests
from bs4 import BeautifulSoup
from settings import APIFY_API_KEY, APIFY_ACTOR_ID, settings

logger = logging.getLogger(__name__)

# Apify Indeed Scraper Actor ID (from settings)


def _parse_indeed_date(date_str: Optional[str]) -> str:
    """
    Parse Indeed's date format from Apify scraper.
    Handles both relative dates (e.g., "2 days ago", "3 weeks ago") and absolute dates.
    
    Args:
        date_str: Date string from Apify (e.g., "2 days ago", "2024-01-15", etc.)
    
    Returns:
        Normalized date string in ISO format (YYYY-MM-DD) or relative format if parsing fails
    """
    if not date_str:
        return ""
    
    date_str = str(date_str).strip()
    
    # Try to parse ISO date format first
    try:
        # Try ISO format: 2024-01-15 or 2024-01-15T10:30:00
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('T')[0])
            return dt.strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        pass
    
    # Parse relative dates like "2 days ago", "3 weeks ago", "1 month ago"
    now = datetime.now()
    
    # Pattern: "X days ago", "X day ago"
    day_match = re.search(r'(\d+)\s+day', date_str.lower())
    if day_match:
        days = int(day_match.group(1))
        date_obj = now - timedelta(days=days)
        return date_obj.strftime('%Y-%m-%d')
    
    # Pattern: "X weeks ago", "X week ago"
    week_match = re.search(r'(\d+)\s+week', date_str.lower())
    if week_match:
        weeks = int(week_match.group(1))
        date_obj = now - timedelta(weeks=weeks)
        return date_obj.strftime('%Y-%m-%d')
    
    # Pattern: "X months ago", "X month ago"
    month_match = re.search(r'(\d+)\s+month', date_str.lower())
    if month_match:
        months = int(month_match.group(1))
        # Approximate: 30 days per month
        date_obj = now - timedelta(days=months * 30)
        return date_obj.strftime('%Y-%m-%d')
    
    # Pattern: "X hours ago", "X hour ago"
    hour_match = re.search(r'(\d+)\s+hour', date_str.lower())
    if hour_match:
        hours = int(hour_match.group(1))
        date_obj = now - timedelta(hours=hours)
        return date_obj.strftime('%Y-%m-%d')
    
    # Pattern: "Just now", "Today", "Yesterday"
    if "just now" in date_str.lower() or "today" in date_str.lower():
        return now.strftime('%Y-%m-%d')
    
    if "yesterday" in date_str.lower():
        date_obj = now - timedelta(days=1)
        return date_obj.strftime('%Y-%m-%d')
    
    # If we can't parse it, return the original string
    logger.debug(f"Could not parse date: {date_str}, returning as-is")
    return date_str


def _filter_jobs_by_date(jobs: List[Dict[str, Any]], date_posted: Optional[str]) -> List[Dict[str, Any]]:
    """
    Filter jobs based on date_posted criteria.
    
    Args:
        jobs: List of job dictionaries with date_posted field
        date_posted: Date filter criteria ("24h", "day", "today", "week", "anytime", "all", or None)
    
    Returns:
        Filtered list of jobs
    """
    if not date_posted or date_posted.lower() in ["anytime", "all", ""]:
        return jobs
    
    date_lower = date_posted.lower()
    now = datetime.now()
    filtered_jobs = []
    
    for job in jobs:
        job_date_str = job.get("date_posted", "")
        if not job_date_str:
            # If no date, include it (can't filter what we don't know)
            filtered_jobs.append(job)
            continue
        
        try:
            # Parse the normalized date (should be YYYY-MM-DD format)
            if re.match(r'^\d{4}-\d{2}-\d{2}', job_date_str):
                job_date = datetime.strptime(job_date_str, '%Y-%m-%d')
                # Calculate difference in days
                diff = (now - job_date).days
                
                # Filter based on criteria
                if "day" in date_lower or "today" in date_lower or "24h" in date_lower or "24" in date_lower:
                    # Within 24 hours = 1 day or less
                    if diff <= 1:
                        filtered_jobs.append(job)
                elif "week" in date_lower:
                    # Within 7 days
                    if diff <= 7:
                        filtered_jobs.append(job)
                elif "month" in date_lower:
                    # Within 30 days
                    if diff <= 30:
                        filtered_jobs.append(job)
                else:
                    # Unknown filter, include the job
                    filtered_jobs.append(job)
            else:
                # Can't parse date, include it to be safe
                filtered_jobs.append(job)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse job date '{job_date_str}' for filtering: {e}")
            # If we can't parse, include it to be safe
            filtered_jobs.append(job)
    
    return filtered_jobs


def search_indeed_jobs(
    job_title: str,
    location: str = "",
    max_results: int = 20,
    date_posted: Optional[str] = None,
    actor_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for jobs on Indeed using Apify API.
    
    Args:
        job_title: Job title to search for
        location: Location to search in (e.g., "Canada", "US", "New York")
        max_results: Maximum number of jobs to return (default: 20)
        date_posted: Filter by date posted ("24h", "day", "today", "week", "anytime", "all", or None)
        actor_id: Apify actor ID (default: uses DEFAULT_ACTOR_ID)
    
    Returns:
        List of job dictionaries filtered by date_posted if specified
    """
    if not job_title:
        raise ValueError("job_title is required")
    
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY is not set in settings")
    
    # Use provided actor_id or from settings
    actor = actor_id or APIFY_ACTOR_ID
    
    # Build Indeed search URL
    if location:
        search_url = f"https://www.indeed.com/jobs?q={job_title}&l={location}"
    else:
        search_url = f"https://www.indeed.com/jobs?q={job_title}"
    
    logger.info(f"Starting Apify scraper for '{job_title}' in '{location}'")
    
    # Trigger the Apify actor run
    # Apify actor IDs use format: username~actor-name (with tilde, not slash)
    # Convert / to ~ if user provided wrong format
    if "/" in actor and "~" not in actor:
        actor = actor.replace("/", "~")
        logger.info(f"Converted actor ID format to use tilde: {actor}")
    
    run_url = f"https://api.apify.com/v2/acts/{actor}/runs?token={APIFY_API_KEY}"
    payload = {
        "startUrls": [{"url": search_url}],
        "maxResults": max_results
    }
    
    try:
        timeout = getattr(settings, 'INDEED_TIMEOUT', 120)
        response = requests.post(run_url, json=payload, timeout=min(30, timeout))
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        
        logger.info(f"Apify run started with ID: {run_id} using actor: {actor}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Actor '{actor}' not found (404). Please check your APIFY_ACTOR_ID.")
            logger.error("Common Indeed scraper actors:")
            logger.error("  - misceres~indeed-scraper")
            logger.error("  - kaitokido~indeed-job-scraper")
            logger.error("Visit https://apify.com/store and search for 'indeed' to find available actors")
            raise ValueError(f"Apify actor '{actor}' not found. Please verify APIFY_ACTOR_ID in your .env file.")
        logger.error(f"Failed to start Apify run: {e}")
        raise
    except requests.RequestException as e:
        logger.error(f"Failed to start Apify run: {e}")
        raise
    
    # Check status of the scraping job until it's done
    status_url = f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}?token={APIFY_API_KEY}"
    
    logger.info("Waiting for Apify scraper to complete...")
    max_wait_time = getattr(settings, 'INDEED_TIMEOUT', 120)  # Use configured timeout
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            logger.warning(f"Apify run timed out after {max_wait_time} seconds")
            raise TimeoutError("Apify scraper took too long to complete")
        
        try:
            status_response = requests.get(status_url, timeout=10)  # Status check is quick
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data["data"]["status"]
            
            if status in ["SUCCEEDED", "FAILED", "ABORTED"]:
                break
            
            logger.debug(f"Apify run status: {status}, waiting...")
            time.sleep(3)  # Wait 3 seconds before checking again
        except requests.RequestException as e:
            logger.warning(f"Error checking Apify status: {e}")
            time.sleep(3)
            continue
    
    # Check if run succeeded
    if status == "FAILED":
        error_message = status_data.get("data", {}).get("statusMessage", "Unknown error")
        logger.error(f"Apify run failed: {error_message}")
        raise RuntimeError(f"Apify scraper failed: {error_message}")
    elif status == "ABORTED":
        logger.error("Apify run was aborted")
        raise RuntimeError("Apify scraper was aborted")
    
    # Get the dataset ID (where results are stored)
    dataset_id = status_data["data"]["defaultDatasetId"]
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json&token={APIFY_API_KEY}"
    
    try:
        timeout = getattr(settings, 'INDEED_TIMEOUT', 120)
        data_response = requests.get(dataset_url, timeout=min(30, timeout))
        data_response.raise_for_status()
        jobs_data = data_response.json()
        
        logger.info(f"Retrieved {len(jobs_data)} jobs from Apify")
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve jobs from Apify dataset: {e}")
        raise
    
    # Clean and normalize the jobs
    cleaned_jobs = []
    for job in jobs_data:
        # Convert HTML description to plain text
        desc_html = job.get("descriptionHTML", "") or job.get("description", "")
        desc_text = ""
        if desc_html:
            try:
                soup = BeautifulSoup(desc_html, "html.parser")
                desc_text = soup.get_text(" ", strip=True)
            except Exception as e:
                logger.debug(f"Could not parse description HTML: {e}")
                desc_text = str(desc_html)
        
        # Extract location components
        location_str = job.get("location", "") or ""
        city = ""
        state = ""
        country = ""
        
        if location_str:
            parts = [p.strip() for p in location_str.split(",")]
            if len(parts) >= 1:
                city = parts[0]
            if len(parts) >= 2:
                state = parts[1]
            if len(parts) >= 3:
                country = parts[2]
        
        # Determine if remote
        remote = False
        job_type_str = ", ".join(job.get("jobType", [])) if job.get("jobType") else ""
        if job_type_str:
            job_type_lower = job_type_str.lower()
            if "remote" in job_type_lower:
                remote = True
            if "hybrid" in job_type_lower:
                remote = True
        
        # Parse and normalize the date
        raw_date = job.get("postedAt") or ""
        normalized_date = _parse_indeed_date(raw_date)
        
        cleaned_jobs.append({
            "title": job.get("positionName") or "",
            "company": job.get("company") or "",
            "location": location_str,
            "city": city,
            "state": state,
            "country": country,
            "url": job.get("externalApplyLink") or job.get("url") or "",
            "date_posted": normalized_date,
            "description": desc_text[:500] if desc_text else "",  # Limit description length
            "employment_type": job_type_str,
            "remote": remote,
            "salary": job.get("salary") or "",
            "rating": job.get("rating"),
            "reviews_count": job.get("reviewsCount"),
        })
    
    logger.info(f"Cleaned and normalized {len(cleaned_jobs)} jobs")
    
    # Filter by date_posted if specified
    if date_posted:
        original_count = len(cleaned_jobs)
        cleaned_jobs = _filter_jobs_by_date(cleaned_jobs, date_posted)
        logger.info(f"Filtered {original_count} jobs to {len(cleaned_jobs)} jobs based on date_posted: {date_posted}")
    
    return cleaned_jobs


def normalize_indeed_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Indeed job data to match the expected format.
    Jobs from Apify are already cleaned, so this mainly ensures format consistency.
    
    Args:
        job: Job dictionary from Apify scraper
    
    Returns:
        Normalized job dictionary
    """
    # Generate a unique job ID from URL
    job_url = job.get("url", "")
    job_id = ""
    
    if job_url:
        # Try to extract job ID from URL
        import re
        jk_match = re.search(r'jk=([a-f0-9]+)', job_url)
        if jk_match:
            job_id = jk_match.group(1)
        else:
            # Fallback: use hash of URL + title + company
            import hashlib
            unique_string = f"{job_url}_{job.get('title', '')}_{job.get('company', '')}"
            job_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
    else:
        # If no URL, create ID from title + company
        import hashlib
        unique_string = f"{job.get('title', '')}_{job.get('company', '')}"
        job_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    normalized = {
        "job_id": job_id,
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "city": job.get("city", ""),
        "state": job.get("state", ""),
        "country": job.get("country", ""),
        "link": job.get("url", ""),
        "date_posted": job.get("date_posted", ""),
        "description": job.get("description", ""),
        "employment_type": job.get("employment_type", ""),
        "remote": job.get("remote", False),
        "salary": job.get("salary", ""),
    }
    
    return normalized
