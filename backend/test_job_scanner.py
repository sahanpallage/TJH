"""
Simple test script for the job scanner.
This script tests the job scanner with sample input data.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.schemas import JobScannerInput, JobScannerResponse
from utils.job_scanner import scan_jobs

def test_job_scanner():
    """Test the job scanner with sample data"""
    
    print("=" * 60)
    print("JOB SCANNER TEST")
    print("=" * 60)
    print()
    
    # Create sample input
    test_input = JobScannerInput(
        job_title="Software Engineer",
        industry="Technology",
        salary_range="$80,000 - $100,000",
        job_type="Remote",
        location_city="San Francisco",
        location_state="CA",
        country="US",
        date_posted="week"
    )
    
    print("Input Parameters:")
    print(f"  Job Title: {test_input.job_title}")
    print(f"  Industry: {test_input.industry}")
    print(f"  Salary Range: {test_input.salary_range}")
    print(f"  Job Type: {test_input.job_type}")
    print(f"  Location: {test_input.location_city}, {test_input.location_state}")
    print(f"  Country: {test_input.country}")
    print(f"  Date Posted: {test_input.date_posted}")
    print()
    print("-" * 60)
    print()
    
    # Check if RAPID_API_KEY is set
    try:
        from settings import RAPID_API_KEY
        if not RAPID_API_KEY:
            print("WARNING: RAPID_API_KEY is not set in settings.py")
            print()
            print("To set your RapidAPI key, choose one of these options:")
            print()
            print("Option 1 - Set in settings.py (quick test):")
            print("  Edit backend/settings.py and uncomment/add:")
            print('  RAPID_API_KEY = "your-rapidapi-key-here"')
            print()
            print("Option 2 - Set as environment variable (PowerShell):")
            print('  $env:RAPID_API_KEY = "your-rapidapi-key-here"')
            print("  Then run: python test_job_scanner.py")
            print()
            print("To get a RapidAPI key:")
            print("  1. Go to https://rapidapi.com/")
            print("  2. Sign up or log in")
            print("  3. Subscribe to 'JSearch' API")
            print("  4. Copy your API key from the dashboard")
            print()
            return None
        print(f"API Key loaded: {RAPID_API_KEY[:10]}..." if len(RAPID_API_KEY) > 10 else "API Key loaded")
    except ImportError as e:
        print("ERROR: Could not import settings.py")
        print(f"Import error: {str(e)}")
        print("Please ensure settings.py exists in the backend directory")
        print(f"Current directory: {Path(__file__).parent}")
        return None
    except Exception as e:
        print(f"ERROR loading settings: {str(e)}")
        return None
    
    # Scan for jobs
    try:
        jobs = scan_jobs(test_input, num_pages=1)
        
        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print()
        
        if jobs:
            print(f"Found {len(jobs)} job(s):")
            print()
            
            for i, job in enumerate(jobs, 1):
                print(f"Job {i}:")
                print(f"  Job Title: {job.job_title}")
                print(f"  Industry: {job.industry or 'N/A'}")
                print(f"  Salary Range: {job.salary_range or 'N/A'}")
                print(f"  Job Type: {job.job_type or 'N/A'}")
                location_str = f"{job.location_city}, {job.location_state}".strip(", ")
                print(f"  Location: {location_str or 'N/A'}")
                print(f"  Country: {job.country or 'N/A'}")
                print(f"  Date Posted: {job.date_posted or 'N/A'}")
                print(f"  Apply Link: {job.apply_link}")
                print()
        else:
            print("No jobs found matching the criteria.")
            print()
            print("Please check:")
            print("  1. RAPID_API_KEY is set correctly in settings.py")
            print("  2. API key is valid and has credits")
            print("  3. Search parameters are correct")
            print("  4. Internet connection is working")
        
        # Create response object
        response = JobScannerResponse(jobs=jobs, count=len(jobs))
        
        print("=" * 60)
        print(f"Test completed. Total jobs: {response.count}")
        print("=" * 60)
        
        return response
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print()
        print("Please ensure:")
        print("  1. settings.py exists and contains RAPID_API_KEY")
        print("  2. All required packages are installed:")
        print("     pip install requests pydantic")
        print("  3. You have a valid RapidAPI key with JSearch API access")
        print("  4. You're subscribed to the JSearch API on RapidAPI")
        print()
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_job_scanner()

