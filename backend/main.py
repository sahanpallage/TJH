from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import requests
from settings import settings, RAPID_API_KEY
from models.schemas import JobScannerInput, JobScannerOutput, JobScannerResponse
from utils.job_scanner import scan_jobs
from utils.theirstack_service import search_jobs_theirstack, normalize_theirstack_job
from services.cache_service import JobCache

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
            print("✅ JSearch cache hit")
            return JobSearchResponse(**cached.data)
        print("ℹ️  JSearch cache miss")

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
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for job in data.get('data', []):
                        apply_link = job.get('job_apply_link', '')
                        if apply_link:
                            raw_jobs_map[apply_link] = job
            except:
                pass
        
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
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")

@app.post("/api/jobs/theirstack", response_model=JobSearchResponse)
async def search_jobs_theirstack_endpoint(request: JobSearchRequest):
    """
    Search for jobs using TheirStack API.
    """
    try:
        # ---------- CACHE CHECK ----------
        cache_payload = request.model_dump()
        cached, hit = cache.get("theirstack", cache_payload, ttl_minutes=60)
        if hit and cached and cached.data.get("jobs"):
            print("✅ TheirStack cache hit")
            return JobSearchResponse(**cached.data)
        print("ℹ️  TheirStack cache miss")

        # Map frontend request to TheirStack parameters
        # Use job title only (don't combine with industry to avoid being too restrictive)
        job_title_or = [request.jobTitle] if request.jobTitle else None
        
        # Map country
        job_country_code_or = None
        if request.country:
            # Convert country name to code if needed
            country_code = request.country.upper() if len(request.country) == 2 else get_country_code(request.country)
            if country_code:
                job_country_code_or = [country_code]
        
        # Map location - be less restrictive, don't require exact city match
        job_location_pattern_or = None
        if request.city:
            # Use city as a pattern, not exact match
            job_location_pattern_or = [request.city]
        
        # Map job type to remote
        remote = None
        if request.jobType == "Remote":
            remote = True
        elif request.jobType == "On-site":
            remote = False
        # For Hybrid, don't set remote filter (let API return both)
        
        # Map date posted
        posted_at_max_age_days = None
        if request.datePosted:
            date_lower = request.datePosted.lower()
            if "day" in date_lower or "today" in date_lower:
                posted_at_max_age_days = 1
            elif "week" in date_lower:
                posted_at_max_age_days = 7
            elif "month" in date_lower:
                posted_at_max_age_days = 30
        
        # Map salary - be less restrictive, only set if both min and max provided
        min_salary_usd = None
        max_salary_usd = None
        # Don't set salary filters if only one is provided (too restrictive)
        if request.salaryMin and request.salaryMax:
            try:
                min_salary_usd = int(request.salaryMin)
                max_salary_usd = int(request.salaryMax)
            except:
                pass
        
        # Call TheirStack API with primary parameters
        jobs_data = search_jobs_theirstack(
            page=0,
            limit=15,
            job_country_code_or=job_country_code_or,
            posted_at_max_age_days=posted_at_max_age_days,
            job_title_or=job_title_or,
            job_location_pattern_or=job_location_pattern_or,
            remote=remote,
            min_salary_usd=min_salary_usd,
            max_salary_usd=max_salary_usd
        )
        
        # If no results and we have restrictive filters, try a fallback with fewer filters
        if not jobs_data and (job_location_pattern_or or remote is not None or min_salary_usd or max_salary_usd):
            print("⚠️  No results with filters, trying fallback search with fewer restrictions...")
            jobs_data = search_jobs_theirstack(
                page=0,
                limit=15,
                job_country_code_or=job_country_code_or,
                posted_at_max_age_days=posted_at_max_age_days,
                job_title_or=job_title_or,
                job_location_pattern_or=None,  # Remove location filter
                remote=None,  # Remove remote filter
                min_salary_usd=None,  # Remove salary filters
                max_salary_usd=None
            )
        
        # Normalize and convert to response format
        # Limit to 15 results for TheirStack
        job_responses = []
        for idx, job in enumerate(jobs_data[:15]):
            normalized = normalize_theirstack_job(job)
            
            # Build location string
            location_parts = []
            if normalized.get("city"):
                location_parts.append(normalized["city"])
            if normalized.get("state"):
                location_parts.append(normalized["state"])
            location = ", ".join(location_parts) if location_parts else normalized.get("location", "")
            
            # Handle remote field - it might be a string or boolean
            remote_value = normalized.get("remote", False)
            if isinstance(remote_value, str):
                remote_value = remote_value.lower() in ["true", "yes", "remote", "1"]
            elif not isinstance(remote_value, bool):
                remote_value = False
            
            job_responses.append(JobResponse(
                id=str(normalized.get("job_id", f"theirstack_{idx}")),
                title=normalized.get("title", ""),
                company=normalized.get("company", ""),
                location=location,
                city=normalized.get("city", ""),
                state=normalized.get("state", ""),
                country=normalized.get("country", ""),
                salary=normalized.get("salary", ""),
                type=normalized.get("employment_type", ""),
                remote=remote_value,
                posted=normalized.get("date_posted", ""),
                description=normalized.get("description", ""),
                applyLink=normalized.get("link", "")
            ))
        
        if len(job_responses) == 0:
            # Return a helpful error message
            raise HTTPException(
                status_code=404,
                detail="No jobs found matching the criteria. Try adjusting your search parameters (e.g., remove location or salary filters)."
            )
        
        return JobSearchResponse(jobs=job_responses, total=len(job_responses))
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        print(f"Error in TheirStack search: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")

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