"""
Accuracy test for the job scanner.
Tests how well the returned jobs match the input criteria.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta
from tabulate import tabulate

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.schemas import JobScannerInput, JobScannerOutput
from utils.job_scanner import scan_jobs

def parse_salary_range(salary_str: str) -> tuple[float, float] | None:
    """Parse salary range string to min and max values"""
    if not salary_str or salary_str == "N/A":
        return None
    
    # Remove currency symbols and commas
    import re
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

def check_salary_match(input_salary: str, output_salary: str) -> bool:
    """Check if output salary matches input salary range"""
    if not input_salary or input_salary == "N/A":
        return True  # No requirement, so any salary matches
    
    input_range = parse_salary_range(input_salary)
    output_range = parse_salary_range(output_salary)
    
    if not input_range or not output_range:
        return True  # Can't determine, assume match
    
    input_min, input_max = input_range
    output_min, output_max = output_range
    
    # Check if there's overlap
    return not (output_max < input_min or output_min > input_max)

def check_date_match(input_date: str, output_date: str) -> bool:
    """Check if output date matches input date requirement"""
    if not input_date or input_date == "N/A":
        return True
    
    if not output_date or output_date == "N/A":
        return False
    
    try:
        # Parse output date
        if 'T' in output_date:
            output_dt = datetime.fromisoformat(output_date.replace('Z', '+00:00'))
        else:
            return True  # Can't parse, assume match
        
        # Calculate time difference
        now = datetime.now(output_dt.tzinfo) if output_dt.tzinfo else datetime.now()
        diff = now - output_dt.replace(tzinfo=None) if output_dt.tzinfo else now - output_dt
        
        input_lower = input_date.lower()
        if "day" in input_lower or "today" in input_lower:
            return diff.days <= 1
        elif "week" in input_lower:
            return diff.days <= 7
        elif "month" in input_lower:
            return diff.days <= 30
        else:
            return True  # Unknown requirement, assume match
    except:
        return True  # Can't parse, assume match

def check_location_match(input_city: str, input_state: str, output_city: str, output_state: str, job_type: str = "") -> bool:
    """Check if output location matches input location"""
    # For remote jobs, location matching is not required
    if job_type and "remote" in job_type.lower():
        return True
    
    if not input_city and not input_state:
        return True  # No location requirement
    
    input_city_lower = input_city.lower() if input_city else ""
    input_state_lower = input_state.lower() if input_state else ""
    output_city_lower = output_city.lower() if output_city else ""
    output_state_lower = output_state.lower() if output_state else ""
    
    # Check city match
    city_match = not input_city_lower or input_city_lower in output_city_lower or output_city_lower in input_city_lower
    
    # Check state match
    state_match = not input_state_lower or input_state_lower in output_state_lower or output_state_lower in input_state_lower
    
    return city_match or state_match  # Match if either city or state matches

def check_job_type_match(input_type: str, output_type: str) -> bool:
    """Check if output job type matches input job type"""
    if not input_type or input_type == "N/A":
        return True
    
    input_lower = input_type.lower()
    output_lower = output_type.lower() if output_type else ""
    
    if input_lower == "remote":
        return "remote" in output_lower
    elif input_lower == "on site" or input_lower == "onsite":
        return "remote" not in output_lower and "hybrid" not in output_lower
    elif input_lower == "hybrid":
        return "hybrid" in output_lower
    return True

def check_job_title_match(input_title: str, output_title: str) -> bool:
    """Check if output job title matches input job title"""
    if not input_title:
        return True
    
    input_words = set(input_title.lower().split())
    output_words = set(output_title.lower().split())
    
    # Check if key words from input are in output
    key_words = [w for w in input_words if len(w) > 3]  # Ignore short words like "the", "and"
    if not key_words:
        key_words = list(input_words)
    
    matches = sum(1 for word in key_words if word in output_words)
    return matches >= len(key_words) * 0.5  # At least 50% of key words should match

def check_industry_match(input_industry: str, output_industry: str) -> bool:
    """Check if output industry matches input industry"""
    if not input_industry or input_industry == "N/A":
        return True
    
    input_lower = input_industry.lower()
    output_lower = output_industry.lower() if output_industry else ""
    
    return input_lower in output_lower or output_lower in input_lower

def check_country_match(input_country: str, output_country: str) -> bool:
    """Check if output country matches input country"""
    if not input_country:
        return True
    
    input_lower = input_country.lower()
    output_lower = output_country.lower() if output_country else ""
    
    # Handle common country codes
    country_map = {
        "us": ["us", "usa", "united states", "united states of america"],
        "uk": ["uk", "gb", "united kingdom", "great britain"],
        "ca": ["ca", "canada"]
    }
    
    if input_lower in country_map:
        return any(c in output_lower for c in country_map[input_lower])
    
    return input_lower in output_lower or output_lower in input_lower

def calculate_accuracy(input_data: JobScannerInput, jobs: List[JobScannerOutput]) -> Dict[str, Any]:
    """Calculate accuracy metrics for job matches"""
    if not jobs:
        return {
            "total_jobs": 0,
            "field_accuracies": {},
            "overall_accuracy": 0.0,
            "detailed_results": []
        }
    
    field_matches = {
        "job_title": [],
        "industry": [],
        "salary_range": [],
        "job_type": [],
        "location": [],
        "country": [],
        "date_posted": []
    }
    
    detailed_results = []
    
    for job in jobs:
        # Check each field
        title_match = check_job_title_match(input_data.job_title, job.job_title)
        industry_match = check_industry_match(input_data.industry, job.industry or "")
        salary_match = check_salary_match(input_data.salary_range, job.salary_range or "")
        job_type_match = check_job_type_match(input_data.job_type, job.job_type or "")
        location_match = check_location_match(
            input_data.location_city, input_data.location_state,
            job.location_city or "", job.location_state or "",
            job.job_type or ""
        )
        country_match = check_country_match(input_data.country, job.country or "")
        date_match = check_date_match(input_data.date_posted, job.date_posted or "")
        
        field_matches["job_title"].append(title_match)
        field_matches["industry"].append(industry_match)
        field_matches["salary_range"].append(salary_match)
        field_matches["job_type"].append(job_type_match)
        field_matches["location"].append(location_match)
        field_matches["country"].append(country_match)
        field_matches["date_posted"].append(date_match)
        
        # Calculate match score for this job
        matches = sum([title_match, industry_match, salary_match, job_type_match, 
                      location_match, country_match, date_match])
        match_score = (matches / 7) * 100
        
        detailed_results.append({
            "job_title": job.job_title,
            "match_score": match_score,
            "matches": {
                "job_title": title_match,
                "industry": industry_match,
                "salary_range": salary_match,
                "job_type": job_type_match,
                "location": location_match,
                "country": country_match,
                "date_posted": date_match
            }
        })
    
    # Calculate field accuracies
    field_accuracies = {}
    for field, matches in field_matches.items():
        if matches:
            field_accuracies[field] = (sum(matches) / len(matches)) * 100
        else:
            field_accuracies[field] = 0.0
    
    # Calculate overall accuracy (average of all field accuracies)
    overall_accuracy = sum(field_accuracies.values()) / len(field_accuracies) if field_accuracies else 0.0
    
    return {
        "total_jobs": len(jobs),
        "field_accuracies": field_accuracies,
        "overall_accuracy": overall_accuracy,
        "detailed_results": detailed_results
    }

def test_accuracy():
    """Run accuracy test for job scanner"""
    
    print("=" * 80)
    print("JOB SCANNER ACCURACY TEST")
    print("=" * 80)
    print()
    
    # Create test input
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
    
    print("INPUT CRITERIA:")
    print(f"  Job Title: {test_input.job_title}")
    print(f"  Industry: {test_input.industry}")
    print(f"  Salary Range: {test_input.salary_range}")
    print(f"  Job Type: {test_input.job_type}")
    print(f"  Location: {test_input.location_city}, {test_input.location_state}")
    print(f"  Country: {test_input.country}")
    print(f"  Date Posted: {test_input.date_posted}")
    print()
    print("-" * 80)
    print()
    
    # Check API key
    try:
        from settings import RAPID_API_KEY
        if not RAPID_API_KEY:
            print("ERROR: RAPID_API_KEY is not set in settings.py")
            return
    except Exception as e:
        print(f"ERROR loading settings: {str(e)}")
        return
    
    # Scan for jobs
    try:
        print("Scanning for jobs...")
        print("Using filtering with 80% minimum match threshold...")
        jobs = scan_jobs(test_input, num_pages=2, strict_filter=True, min_match_threshold=80.0)  # 80% threshold
        
        if not jobs:
            print("No jobs found. Cannot calculate accuracy.")
            return
        
        print(f"Found {len(jobs)} jobs. Calculating accuracy...")
        print()
        
        # Calculate accuracy
        accuracy_results = calculate_accuracy(test_input, jobs)
        
        # Display results
        print("=" * 80)
        print("ACCURACY RESULTS")
        print("=" * 80)
        print()
        
        # Field accuracy table
        field_data = []
        for field, accuracy in accuracy_results["field_accuracies"].items():
            field_name = field.replace("_", " ").title()
            field_data.append([field_name, f"{accuracy:.2f}%", "✓" if accuracy >= 80 else "⚠" if accuracy >= 50 else "✗"])
        
        print("FIELD ACCURACY:")
        print(tabulate(field_data, headers=["Field", "Accuracy", "Status"], tablefmt="grid", floatfmt=".2f"))
        print()
        
        # Overall accuracy
        overall = accuracy_results["overall_accuracy"]
        print(f"OVERALL ACCURACY: {overall:.2f}%")
        print()
        
        # Detailed results table
        print("=" * 80)
        print("DETAILED JOB MATCHES")
        print("=" * 80)
        print()
        
        detailed_data = []
        for result in accuracy_results["detailed_results"]:
            matches = result["matches"]
            match_indicators = [
                "✓" if matches["job_title"] else "✗",
                "✓" if matches["industry"] else "✗",
                "✓" if matches["salary_range"] else "✗",
                "✓" if matches["job_type"] else "✗",
                "✓" if matches["location"] else "✗",
                "✓" if matches["country"] else "✗",
                "✓" if matches["date_posted"] else "✗"
            ]
            
            detailed_data.append([
                result["job_title"][:40] + "..." if len(result["job_title"]) > 40 else result["job_title"],
                f"{result['match_score']:.1f}%",
                "".join(match_indicators)
            ])
        
        print(tabulate(
            detailed_data,
            headers=["Job Title", "Match Score", "T|I|S|J|L|C|D"],
            tablefmt="grid"
        ))
        print()
        print("Legend: T=Title, I=Industry, S=Salary, J=Job Type, L=Location, C=Country, D=Date Posted")
        print("       ✓ = Match, ✗ = No Match")
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Jobs Analyzed: {accuracy_results['total_jobs']}")
        print(f"Overall Accuracy: {overall:.2f}%")
        
        perfect_matches = sum(1 for r in accuracy_results["detailed_results"] if r["match_score"] == 100.0)
        print(f"Perfect Matches (100%): {perfect_matches}/{accuracy_results['total_jobs']}")
        print(f"High Quality Matches (≥80%): {sum(1 for r in accuracy_results['detailed_results'] if r['match_score'] >= 80)}/{accuracy_results['total_jobs']}")
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_accuracy()

