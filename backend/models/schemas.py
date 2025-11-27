from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Literal, Dict, Any

class JobSearchRequest(BaseModel):
    query1: str
    industry: Optional[str] = ""
    salary_range: Optional[str] = ""
    job_type: Optional[str] = "any"
    work_type: Optional[str] = "any"
    location: Optional[str] = ""
    country: Optional[str] = "us"
    date_posted: Optional[str] = "all"
    limit: Optional[int] = 10

class Job(BaseModel):
    employer_name: str
    job_title: str
    job_city: Optional[str] = None
    job_country: Optional[str] = None
    job_description: str
    job_apply_link: str
    job_id: Optional[str] = None
    job_employment_type: Optional[str] = None
    job_salary_min: Optional[float] = None
    job_salary_max: Optional[float] = None
    job_salary_currency: Optional[str] = None
    match_score: Optional[float] = None

class JobSearchResponse(BaseModel):
    jobs: List[Job]
    count: int

class JobDetailsRequest(BaseModel):
    url: str

class FormFillRequest(BaseModel):
    url: str
    resume_url: Optional[str] = None

class FormFillResponse(BaseModel):
    session_id: str
    live_view_url: str
    browser_url: str
    message: str

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    message: Optional[str] = None

class TemplateInfo(BaseModel):
    name: str
    path: str

class TemplateContent(BaseModel):
    name: str
    content: str

class OverleafLinkRequest(BaseModel):
    latex_content: str

class OverleafLinkResponse(BaseModel):
    overleaf_link: str

class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str

class AgentQueryRequest(BaseModel):
    messages: List[AgentMessage]
    resume_text: Optional[str] = ""
    job_text: Optional[str] = ""
    preferred_country: Optional[str] = "us"
    date_posted: Optional[str] = "week"
    limit: Optional[int] = 10

class AgentQueryResponse(BaseModel):
    summary: str
    query: Dict[str, Any]
    jobs: List[Job]

class DocumentExtractionResponse(BaseModel):
    text_preview: str
    characters: int

class JobScannerInput(BaseModel):
    """Input schema for job scanner"""
    job_title: str
    industry: Optional[str] = ""
    salary_range: Optional[str] = ""
    job_type: Literal["On site", "Remote", "Hybrid"] = "Remote"
    location_city: Optional[str] = ""
    location_state: Optional[str] = ""
    country: Optional[str] = "US"
    date_posted: Optional[str] = ""

class JobScannerOutput(BaseModel):
    """Output schema for job scanner - same as input plus apply link"""
    job_title: str
    industry: Optional[str] = ""
    salary_range: Optional[str] = ""
    job_type: Optional[str] = ""
    location_city: Optional[str] = ""
    location_state: Optional[str] = ""
    country: Optional[str] = ""
    date_posted: Optional[str] = ""
    apply_link: str  # Link to apply for the job

class JobScannerResponse(BaseModel):
    """Response containing list of job scanner results"""
    jobs: List[JobScannerOutput]
    count: int