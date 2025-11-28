import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import requests

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.schemas import JobScannerInput, JobScannerOutput
from settings import RAPID_API_KEY


logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 10

def _parse_salary_range(salary_str: str) -> tuple[float, float] | None:
    """Parse salary range string to min and max values"""
    if not salary_str or salary_str == "N/A":
        return None
    numbers = re.findall(r'[\d,]+', salary_str.replace(',', ''))
    if len(numbers) >= 2:
        try:
            return (float(numbers[0].replace(',', '')), float(numbers[1].replace(',', '')))
        except:
            pass
    elif len(numbers) == 1:
        try:
            val = float(numbers[0].replace(',', ''))
            return (val, val)
        except:
            pass
    return None

def _calculate_job_match_score(input_data: JobScannerInput, job: dict[str, Any]) -> float:
    """Calculate match score (0-100) for a job based on input criteria"""
    matches = []
    total_checks = 0
    
    # Check job title (required)
    total_checks += 1
    job_title = job.get('job_title', '').lower()
    input_title = input_data.job_title.lower()
    input_words = set(input_title.split())
    job_words = set(job_title.split())
    key_words = [w for w in input_words if len(w) > 3]
    if key_words:
        title_match = sum(1 for word in key_words if word in job_words) >= len(key_words) * 0.5
    else:
        title_match = input_title in job_title or job_title in input_title
    matches.append(title_match)
    
    # Check job type
    if input_data.job_type:
        total_checks += 1
        is_remote = job.get('job_is_remote', False)
        if input_data.job_type == "Remote":
            job_type_match = is_remote
        elif input_data.job_type == "On site":
            job_type_match = not is_remote
        elif input_data.job_type == "Hybrid":
            job_desc = job.get('job_description', '').lower()
            job_type_match = 'hybrid' in job_desc or 'hybrid' in job_title
        else:
            job_type_match = True
        matches.append(job_type_match)
    
    # Check location (skip for remote jobs)
    if input_data.location_city or input_data.location_state:
        if input_data.job_type != "Remote":
            total_checks += 1
            job_city = (job.get('job_city') or '').lower()
            job_state = (job.get('job_state') or '').lower()
            input_city = (input_data.location_city or '').lower()
            input_state = (input_data.location_state or '').lower()

            # Stricter matching: if city is provided, require city equality;
            # if state is provided, require state equality.
            city_match = True
            state_match = True

            if input_city:
                city_match = input_city == job_city
            if input_state:
                state_match = input_state == job_state

            if input_city and input_state:
                matches.append(city_match and state_match)
            else:
                matches.append(city_match and state_match or city_match or state_match)
        # For remote jobs, location match is always True
        elif input_data.job_type == "Remote":
            total_checks += 1
            matches.append(True)
    
    # Check country
    if input_data.country:
        total_checks += 1
        job_country = (job.get('job_country') or "").lower()
        input_country = (input_data.country or "").lower()
        country_map = {
            "us": ["us", "usa", "united states"],
            "uk": ["uk", "gb", "united kingdom"],
            "ca": ["ca", "canada"]
        }
        if input_country in country_map:
            country_match = any(c in job_country for c in country_map[input_country])
        else:
            country_match = input_country in job_country or job_country in input_country
        matches.append(country_match)
    
    # Check salary range
    if input_data.salary_range:
        total_checks += 1
        input_range = _parse_salary_range(input_data.salary_range)
        salary_min = job.get('job_min_salary')
        salary_max = job.get('job_max_salary')
        if input_range and salary_min and salary_max:
            input_min, input_max = input_range
            # Check if there's overlap
            salary_match = not (salary_max < input_min or salary_min > input_max)
        else:
            salary_match = True  # Can't verify, assume match
        matches.append(salary_match)
    
    # Check date posted
    if input_data.date_posted:
        total_checks += 1
        date_posted_str = job.get('job_posted_at_datetime_utc', '')
        if date_posted_str:
            try:
                if 'T' in date_posted_str:
                    job_dt = datetime.fromisoformat(date_posted_str.replace('Z', '+00:00'))
                    now = datetime.now(job_dt.tzinfo) if job_dt.tzinfo else datetime.now()
                    diff = now - job_dt.replace(tzinfo=None) if job_dt.tzinfo else now - job_dt
                    date_lower = input_data.date_posted.lower()
                    if "day" in date_lower or "today" in date_lower:
                        date_match = diff.days <= 1
                    elif "week" in date_lower:
                        date_match = diff.days <= 7
                    elif "month" in date_lower:
                        date_match = diff.days <= 30
                    else:
                        date_match = True
                else:
                    date_match = True
            except:
                date_match = True
        else:
            date_match = True  # Can't verify, assume match
        matches.append(date_match)
    
    if total_checks == 0:
        return 100.0  # No criteria to check
    
    match_score = (sum(matches) / total_checks) * 100
    return match_score

def _check_job_matches_criteria(input_data: JobScannerInput, job: dict[str, Any], min_match_threshold: float = 100.0) -> bool:
    """Check if a job matches input criteria with a minimum match threshold"""
    match_score = _calculate_job_match_score(input_data, job)
    return match_score >= min_match_threshold
    # Check job title
    job_title = job.get('job_title', '').lower()
    input_title = input_data.job_title.lower()
    input_words = set(input_title.split())
    job_words = set(job_title.split())
    key_words = [w for w in input_words if len(w) > 3]
    if key_words:
        title_match = sum(1 for word in key_words if word in job_words) >= len(key_words) * 0.5
    else:
        title_match = input_title in job_title or job_title in input_title
    if not title_match:
        return False
    
    # Check job type
    if input_data.job_type:
        is_remote = job.get('job_is_remote', False)
        if input_data.job_type == "Remote" and not is_remote:
            return False
        elif input_data.job_type == "On site" and is_remote:
            return False
        elif input_data.job_type == "Hybrid":
            # For hybrid, check if it's mentioned in title or description
            job_desc = job.get('job_description', '').lower()
            if 'hybrid' not in job_desc and 'hybrid' not in job_title:
                return False
    
    # Check location (skip for remote jobs as they can be done from anywhere)
    if input_data.job_type != "Remote" and (input_data.location_city or input_data.location_state):
        job_city = (job.get('job_city') or '').lower()
        job_state = (job.get('job_state') or '').lower()
        input_city = (input_data.location_city or '').lower()
        input_state = (input_data.location_state or '').lower()

        # Stricter matching: when city is set, require exact city match;
        # when state is set, require exact state match.
        city_match = True
        state_match = True

        if input_city:
            city_match = input_city == job_city
        if input_state:
            state_match = input_state == job_state

        if input_city and input_state:
            if not (city_match and state_match):
                return False
        else:
            if not (city_match or state_match):
                return False
    
    # Check country
    if input_data.country:
        job_country = (job.get('job_country') or '').lower()
        input_country = input_data.country.lower()
        country_map = {
            "us": ["us", "usa", "united states"],
            "uk": ["uk", "gb", "united kingdom"],
            "ca": ["ca", "canada"]
        }
        if input_country in country_map:
            country_match = any(c in job_country for c in country_map[input_country])
        else:
            country_match = input_country in job_country or job_country in input_country
        if not country_match:
            return False
    
    # Check salary range
    if input_data.salary_range:
        input_range = _parse_salary_range(input_data.salary_range)
        salary_min = job.get('job_min_salary')
        salary_max = job.get('job_max_salary')
        if input_range and salary_min and salary_max:
            input_min, input_max = input_range
            # Check if there's overlap (jobs within or overlapping the requested range)
            if salary_max < input_min or salary_min > input_max:
                return False
    
    # Check date posted
    if input_data.date_posted:
        date_posted_str = job.get('job_posted_at_datetime_utc', '')
        if date_posted_str:
            try:
                if 'T' in date_posted_str:
                    job_dt = datetime.fromisoformat(date_posted_str.replace('Z', '+00:00'))
                    now = datetime.now(job_dt.tzinfo) if job_dt.tzinfo else datetime.now()
                    diff = now - job_dt.replace(tzinfo=None) if job_dt.tzinfo else now - job_dt
                    
                    date_lower = input_data.date_posted.lower()
                    if "day" in date_lower or "today" in date_lower:
                        if diff.days > 1:
                            return False
                    elif "week" in date_lower:
                        if diff.days > 7:
                            return False
                    elif "month" in date_lower:
                        if diff.days > 30:
                            return False
            except:
                pass  # If we can't parse, allow it
    
    return True

def scan_jobs(input_data: JobScannerInput, num_pages: int = 1, strict_filter: bool = False, min_match_threshold: float = 80.0) -> List[JobScannerOutput]:
    """
    Scans for jobs using JSearch API based on input criteria.
    
    :param input_data: JobScannerInput containing search criteria
    :param num_pages: Number of pages to fetch (default 1)
    :return: List of JobScannerOutput with job details and apply links
    """
    url = "https://jsearch.p.rapidapi.com/search"
    headers: dict[str, Any] = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # Build query from job title, industry, and location (as recommended by JSearch docs)
    # e.g. "software engineer technology San Francisco CA US"
    query_parts = [input_data.job_title]
    if input_data.industry:
        query_parts.append(input_data.industry)
    if input_data.location_city:
        query_parts.append(input_data.location_city)
    if input_data.location_state:
        query_parts.append(input_data.location_state)
    if input_data.country:
        query_parts.append(input_data.country)
    query = " ".join(query_parts)
    
    # Build location string (still sent as a separate hint parameter)
    location_parts = []
    if input_data.location_city:
        location_parts.append(input_data.location_city)
    if input_data.location_state:
        location_parts.append(input_data.location_state)
    location = ", ".join(location_parts) if location_parts else ""
    
    # Map job_type to JSearch format
    # JSearch now uses `work_from_home` (boolean) to return only remote jobs.
    work_from_home: Optional[str] = None
    if input_data.job_type == "Remote":
        work_from_home = "true"
    
    # Map date_posted to JSearch format (all, day, week, month)
    date_posted = "all"
    if input_data.date_posted:
        date_lower = input_data.date_posted.lower()
        if "day" in date_lower or "today" in date_lower:
            date_posted = "day"
        elif "week" in date_lower:
            date_posted = "week"
        elif "month" in date_lower:
            date_posted = "month"
    
    all_jobs: List[JobScannerOutput] = []

    logger.info(
        "Searching for jobs with JSearch",
        extra={
            "query": query,
            "location": location or "Any",
            "country": input_data.country,
            "job_type": input_data.job_type,
            "date_posted": date_posted,
        },
    )
    
    for page in range(1, num_pages + 1):
        params: dict[str, Any] = {
            "query": query,
            "page": str(page),
            "num_pages": "1"
        }
        
        # Add optional parameters
        if location:
            params["location"] = location
        if input_data.country:
            params["country"] = input_data.country.lower()
        if work_from_home is not None:
            params["work_from_home"] = work_from_home
        if date_posted:
            params["date_posted"] = date_posted
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                response_data = response.json()
                jobs_data: List[dict[str, Any]] = response_data.get("data", [])
                logger.info(
                    "JSearch page fetched",
                    extra={"page": page, "jobs_on_page": len(jobs_data)},
                )

                for job in jobs_data:
                    # Apply filtering if enabled
                    if strict_filter:
                        threshold = 100.0 if min_match_threshold >= 100.0 else min_match_threshold
                        if not _check_job_matches_criteria(input_data, job, threshold):
                            continue
                    
                    # Extract job details
                    job_title = job.get('job_title', input_data.job_title)
                    apply_link = job.get('job_apply_link', '')
                    
                    # Extract location info
                    job_city = job.get('job_city', input_data.location_city or '')
                    job_state = job.get('job_state', input_data.location_state or '')
                    job_country = job.get('job_country', input_data.country or '')
                    
                    # Extract salary info
                    salary_min = job.get('job_min_salary')
                    salary_max = job.get('job_max_salary')
                    salary_currency = job.get('job_salary_currency', 'USD')
                    
                    salary_range = input_data.salary_range or ""
                    if salary_min and salary_max:
                        salary_range = f"{salary_currency} {salary_min:,} - {salary_max:,}"
                    elif salary_min:
                        salary_range = f"{salary_currency} {salary_min:,}+"
                    
                    # Extract job type
                    employment_type = job.get('job_employment_type', '')
                    job_type = input_data.job_type
                    if employment_type:
                        if 'FULLTIME' in employment_type.upper():
                            job_type = "On site" if not job.get('job_is_remote', False) else "Remote"
                        elif job.get('job_is_remote', False):
                            job_type = "Remote"
                    
                    # Extract date posted
                    date_posted_str = job.get('job_posted_at_datetime_utc', '')
                    if not date_posted_str:
                        date_posted_str = input_data.date_posted or ""
                    
                    # Extract industry (from job description or employer)
                    industry = input_data.industry or ""
                    employer_name = job.get('employer_name', '')
                    
                    # Create output
                    job_output = JobScannerOutput(
                        job_title=job_title,
                        industry=industry,
                        salary_range=salary_range,
                        job_type=job_type,
                        location_city=job_city,
                        location_state=job_state,
                        country=job_country,
                        date_posted=date_posted_str,
                        apply_link=apply_link
                    )
                    all_jobs.append(job_output)
            else:
                logger.warning(
                    "Error fetching jobs from JSearch",
                    extra={
                        "page": page,
                        "status_code": response.status_code,
                        "response_text": response.text[:500],
                    },
                )
        except requests.RequestException as e:
            logger.error(
                "Exception occurred while fetching jobs from JSearch",
                extra={"page": page, "error": str(e)},
            )

    logger.info("Total jobs found", extra={"total": len(all_jobs)})
    return all_jobs

