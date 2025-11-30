"""
Indeed Job Scraper Service using Apify API.
Based on the implementation in "Indeed scrapper" folder.
Uses Apify's Indeed scraper actor which handles Cloudflare and other protections.
"""
import logging
import time
from typing import Optional, List, Dict, Any
import requests
from bs4 import BeautifulSoup
from settings import APIFY_API_KEY, APIFY_ACTOR_ID

logger = logging.getLogger(__name__)

# Apify Indeed Scraper Actor ID (from settings)


def search_indeed_jobs(
    job_title: str,
    location: str = "",
    max_results: int = 20,
    actor_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for jobs on Indeed using Apify API.
    
    Args:
        job_title: Job title to search for
        location: Location to search in (e.g., "Canada", "US", "New York")
        max_results: Maximum number of jobs to return (default: 20)
        actor_id: Apify actor ID (default: uses DEFAULT_ACTOR_ID)
    
    Returns:
        List of job dictionaries
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
        response = requests.post(run_url, json=payload, timeout=30)
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
    max_wait_time = 120  # Maximum 2 minutes
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            logger.warning(f"Apify run timed out after {max_wait_time} seconds")
            raise TimeoutError("Apify scraper took too long to complete")
        
        try:
            status_response = requests.get(status_url, timeout=10)
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
        data_response = requests.get(dataset_url, timeout=30)
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
        
        cleaned_jobs.append({
            "title": job.get("positionName") or "",
            "company": job.get("company") or "",
            "location": location_str,
            "city": city,
            "state": state,
            "country": country,
            "url": job.get("externalApplyLink") or job.get("url") or "",
            "date_posted": job.get("postedAt") or "",
            "description": desc_text[:500] if desc_text else "",  # Limit description length
            "employment_type": job_type_str,
            "remote": remote,
            "salary": job.get("salary") or "",
            "rating": job.get("rating"),
            "reviews_count": job.get("reviewsCount"),
        })
    
    logger.info(f"Cleaned and normalized {len(cleaned_jobs)} jobs")
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
