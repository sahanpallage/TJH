import asyncio
import logging
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from settings import settings, RAPID_API_KEY
from models.schemas import JobScannerInput, JobScannerOutput, JobScannerResponse
from utils.job_scanner import scan_jobs
from utils.indeed_service import search_indeed_jobs, normalize_indeed_job
from utils.linkedin_jobspy_service import search_linkedin_jobs
from services.cache_service import JobCache

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 10

app = FastAPI(title="Job Search API", version="1.0.0")
cache = JobCache()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model for frontend
class JobSearchRequest(BaseModel):
    jobTitle: str
    industry: Optional[str] = ""
    salaryMin: Optional[str] = ""
    salaryMax: Optional[str] = ""
    jobType: Optional[str] = ""
    city: Optional[str] = ""
    country: Optional[str] = ""
    datePosted: Optional[str] = ""

# Response model for frontend
class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    city: str
    state: str
    country: str
    salary: str
    type: str
    remote: bool
    posted: str
    description: str
    applyLink: str

class JobSearchResponse(BaseModel):
    jobs: List[JobResponse]
    total: int

@app.get("/")
async def root():
    return {"message": "Job Search API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/jobs/jsearch", response_model=JobSearchResponse)
async def search_jobs_jsearch(request: JobSearchRequest):
    """
    Search for jobs using JSearch (RapidAPI) with filtering and accuracy checking.
    """
    try:
        # ---------- CACHE CHECK ----------
        cache_payload = request.model_dump()
        cached, hit = cache.get("jsearch", cache_payload, ttl_minutes=60)
        if hit and cached and cached.data.get("jobs"):
            logger.info("JSearch cache hit")
            return JobSearchResponse(**cached.data)
        logger.info("JSearch cache miss")

        # Map frontend request to JobScannerInput
        # Map jobType: "Remote" -> "Remote", "On-site" -> "On site", "Hybrid" -> "Hybrid"
        job_type_mapping = {
            "Remote": "Remote",
            "On-site": "On site",
            "Hybrid": "Hybrid",
            "Full-time": "Remote",  # Default mapping
            "Part-time": "Remote",   # Default mapping
        }
        job_type = job_type_mapping.get(request.jobType, "Remote")
        
        # Build salary range string if provided
        salary_range = ""
        if request.salaryMin or request.salaryMax:
            if request.salaryMin and request.salaryMax:
                salary_range = f"${request.salaryMin} - ${request.salaryMax}"
            elif request.salaryMin:
                salary_range = f"${request.salaryMin}+"
            elif request.salaryMax:
                salary_range = f"Up to ${request.salaryMax}"
        
        # Create JobScannerInput
        scanner_input = JobScannerInput(
            job_title=request.jobTitle,
            industry=request.industry or "",
            salary_range=salary_range,
            job_type=job_type,
            location_city=request.city or "",
            location_state="",  # Frontend doesn't send state separately
            country=request.country.upper() if request.country else "US",
            date_posted=request.datePosted or ""
        )
        
        # Call scan_jobs with filtering enabled (like the test)
        # We'll also need to get raw job data for company and description
        
        # Build query and params (same logic as scan_jobs)
        query_parts = [scanner_input.job_title]
        if scanner_input.industry:
            query_parts.append(scanner_input.industry)
        query = " ".join(query_parts)
        
        location_parts = []
        if scanner_input.location_city:
            location_parts.append(scanner_input.location_city)
        location = ", ".join(location_parts) if location_parts else ""
        
        remote_jobs_only = None
        if scanner_input.job_type == "Remote":
            remote_jobs_only = "true"
        elif scanner_input.job_type == "On site":
            remote_jobs_only = "false"
        
        date_posted = "all"
        if scanner_input.date_posted:
            date_lower = scanner_input.date_posted.lower()
            if "day" in date_lower or "today" in date_lower:
                date_posted = "day"
            elif "week" in date_lower:
                date_posted = "week"
            elif "month" in date_lower:
                date_posted = "month"
        
        # Get filtered jobs using scan_jobs
        filtered_jobs = scan_jobs(
            scanner_input,
            num_pages=2,
            strict_filter=True,
            min_match_threshold=80.0
        )
        
        # Get raw job data to extract company and description
        # We'll match by apply_link to get full details
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        raw_jobs_map = {}
        for page in range(1, 3):
            params = {
                "query": query,
                "page": str(page),
                "num_pages": "1"
            }
            if location:
                params["location"] = location
            if scanner_input.country:
                params["country"] = scanner_input.country.lower()
            if remote_jobs_only:
                params["remote_jobs_only"] = remote_jobs_only
            if date_posted != "all":
                params["date_posted"] = date_posted
            
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                if response.status_code == 200:
                    data = response.json()
                    for job in data.get("data", []):
                        apply_link = job.get("job_apply_link", "")
                        if apply_link:
                            raw_jobs_map[apply_link] = job
                else:
                    logger.warning(
                        "JSearch raw job fetch failed",
                        extra={
                            "page": page,
                            "status_code": response.status_code,
                            "response_text": response.text[:500],
                        },
                    )
            except requests.RequestException as e:
                logger.error(
                    "Error fetching raw JSearch jobs",
                    extra={"page": page, "error": str(e)},
                )
        
        # Convert JobScannerOutput to JobResponse format with full details
        # Limit to 15 results for JSearch
        job_responses: List[JobResponse] = []
        for idx, job in enumerate(filtered_jobs[:15]):
            # Get raw job data if available
            raw_job = raw_jobs_map.get(job.apply_link, {})
            
            # Build location string
            location_parts = []
            if job.location_city:
                location_parts.append(job.location_city)
            if job.location_state:
                location_parts.append(job.location_state)
            location = ", ".join(location_parts) if location_parts else ""
            
            # Extract description
            description = raw_job.get('job_description', '') or raw_job.get('job_highlights', {}).get('summary', [None])[0] or ""
            
            job_responses.append(JobResponse(
                id=f"jsearch_{idx}_{job.apply_link[:20]}" if job.apply_link else f"jsearch_{idx}",
                title=job.job_title,
                company=raw_job.get('employer_name', ''),
                location=location,
                city=job.location_city or "",
                state=job.location_state or "",
                country=job.country or "",
                salary=job.salary_range or "",
                type=job.job_type or "",
                remote=job.job_type == "Remote" if job.job_type else False,
                posted=job.date_posted or "",
                description=description[:500] if description else "",  # Limit description length
                applyLink=job.apply_link
            ))
        
        response_obj = JobSearchResponse(jobs=job_responses, total=len(job_responses))

        # ---------- CACHE STORE ----------
        cache.set("jsearch", cache_payload, response_obj.model_dump())

        return response_obj

    except Exception as e:
        logger.exception("Unhandled error in JSearch endpoint")
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")

@app.post("/api/jobs/indeed", response_model=JobSearchResponse)
async def search_jobs_indeed_endpoint(request: JobSearchRequest):
    """
    Search for jobs using Indeed scraper (Playwright).
    """
    try:
        # ---------- CACHE CHECK ----------
        cache_payload = request.model_dump()
        cached, hit = cache.get("indeed", cache_payload, ttl_minutes=60)
        if hit and cached and cached.data.get("jobs"):
            logger.info("Indeed cache hit")
            return JobSearchResponse(**cached.data)
        logger.info("Indeed cache miss")

        # Build location string from city and country
        location_parts = []
        if request.city:
            location_parts.append(request.city)
        if request.country:
            location_parts.append(request.country)
        location = ", ".join(location_parts) if location_parts else (request.country or "")
        
        # Call Indeed scraper (Apify API) - run in executor since it's sync
        logger.info(f"Searching Indeed for '{request.jobTitle}' in '{location}'")
        loop = asyncio.get_event_loop()
        jobs_data = await loop.run_in_executor(
            None,
            search_indeed_jobs,
            request.jobTitle,
            location,
            30  # max_results - capped at 30
        )
        
        # Normalize and convert to response format
        job_responses = []
        seen_ids = set()  # Track IDs to ensure uniqueness
        
        # Process all jobs returned by Apify (capped at 30)
        for idx, job in enumerate(jobs_data[:30]):
            normalized = normalize_indeed_job(job)
            
            # Build location string
            loc_parts = []
            if normalized.get("city"):
                loc_parts.append(normalized["city"])
            if normalized.get("state"):
                loc_parts.append(normalized["state"])
            if normalized.get("country"):
                loc_parts.append(normalized["country"])
            location_str = ", ".join(loc_parts) if loc_parts else normalized.get("location", "")
            
            # Handle remote field
            remote_value = normalized.get("remote", False)
            if isinstance(remote_value, str):
                remote_value = remote_value.lower() in ["true", "yes", "remote", "1"]
            elif not isinstance(remote_value, bool):
                remote_value = False
            
            # Generate unique ID, ensuring no duplicates
            base_id = normalized.get("job_id", "")
            if not base_id:
                base_id = f"indeed_{idx}"
            
            # If ID already seen, append index to make it unique
            job_id = base_id
            counter = 0
            while job_id in seen_ids:
                counter += 1
                job_id = f"{base_id}_{counter}"
            
            seen_ids.add(job_id)
            
            job_responses.append(JobResponse(
                id=f"indeed_{job_id}",  # Prefix with "indeed_" for clarity
                title=normalized.get("title", ""),
                company=normalized.get("company", ""),
                location=location_str,
                city=normalized.get("city", ""),
                state=normalized.get("state", ""),
                country=normalized.get("country", ""),
                salary=normalized.get("salary", ""),
                type=normalized.get("employment_type", ""),
                remote=remote_value,
                posted=normalized.get("date_posted", ""),
                description=normalized.get("description", "")[:500] if normalized.get("description") else "",
                applyLink=normalized.get("link", "")
            ))
        
        response_obj = JobSearchResponse(jobs=job_responses, total=len(job_responses))

        # ---------- CACHE STORE ----------
        cache.set("indeed", cache_payload, response_obj.model_dump())
        
        if len(job_responses) == 0:
            logger.warning(f"No jobs found for search: '{request.jobTitle}' in '{location}'")
            # Provide more helpful error message
            if len(jobs_data) == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No jobs found on Indeed. The search might not have returned any results, or the page structure may have changed. Try adjusting your search parameters."
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Found {len(jobs_data)} jobs but none could be processed. This might be due to page structure changes on Indeed."
                )
        
        return response_obj
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        logger.exception(f"Unhandled error in Indeed endpoint: {error_msg}")
        # Provide more helpful error message
        if "Playwright browsers are not installed" in error_msg:
            detail_msg = "Playwright browsers are not installed. Please run 'playwright install chromium' in the backend directory."
        else:
            detail_msg = f"Error searching Indeed jobs: {error_msg}"
        raise HTTPException(status_code=500, detail=detail_msg)

def get_country_code(country_name: str) -> Optional[str]:
    """Convert country name to country code"""
    country_map = {
        "united states": "US",
        "usa": "US",
        "us": "US",
        "united kingdom": "GB",
        "uk": "GB",
        "canada": "CA",
        "australia": "AU",
        "germany": "DE",
        "france": "FR",
        "spain": "ES",
        "italy": "IT",
        "netherlands": "NL",
        "sweden": "SE",
        "norway": "NO",
        "denmark": "DK",
        "finland": "FI",
        "poland": "PL",
        "india": "IN",
        "china": "CN",
        "japan": "JP",
        "south korea": "KR",
        "singapore": "SG",
        "brazil": "BR",
        "mexico": "MX",
        "argentina": "AR",
        "south africa": "ZA",
    }
    normalized = country_name.lower().strip()
    return country_map.get(normalized, normalized.upper() if len(normalized) == 2 else None)


@app.post("/api/jobs/linkedin", response_model=JobSearchResponse)
async def search_jobs_linkedin_endpoint(request: JobSearchRequest):
    """
    Search for jobs directly on LinkedIn using the JobSpy scraper.
    Kept separate from JSearch and Indeed, but returns the same shape.
    """
    try:
        # ---------- CACHE CHECK ----------
        cache_payload = request.model_dump()
        cached, hit = cache.get("linkedin", cache_payload, ttl_minutes=60)
        if hit and cached and cached.data.get("jobs"):
            logger.info("LinkedIn cache hit")
            return JobSearchResponse(**cached.data)
        logger.info("LinkedIn cache miss")

        jobs_data = search_linkedin_jobs(
            job_title=request.jobTitle,
            industry=request.industry or "",
            city=request.city or "",
            country=request.country or "",
            date_posted=request.datePosted or "",
            results_wanted=30,
        )

        # Limit to 30 for LinkedIn
        job_responses: List[JobResponse] = []
        for idx, job in enumerate(jobs_data[:30]):
            job_responses.append(
                JobResponse(
                    id=str(job.get("id", f"linkedin_{idx}")),
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    location=job.get("location", ""),
                    city=job.get("city", ""),
                    state=job.get("state", ""),
                    country=job.get("country", ""),
                    salary=job.get("salary", ""),
                    type=job.get("type", ""),
                    remote=bool(job.get("remote", False)),
                    posted=job.get("posted", ""),
                    description=job.get("description", ""),
                    applyLink=job.get("applyLink", ""),
                )
            )

        response_obj = JobSearchResponse(jobs=job_responses, total=len(job_responses))

        # ---------- CACHE STORE ----------
        cache.set("linkedin", cache_payload, response_obj.model_dump())

        if len(job_responses) == 0:
            raise HTTPException(
                status_code=404,
                detail="No LinkedIn jobs found matching the criteria. Try adjusting your search parameters.",
            )

        return response_obj

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception("Unhandled error in LinkedIn endpoint")
        raise HTTPException(status_code=500, detail=f"Error searching LinkedIn jobs: {str(e)}")
