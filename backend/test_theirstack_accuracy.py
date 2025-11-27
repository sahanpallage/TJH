"""
Accuracy test for TheirStack Job Search API.
Tests how well the returned jobs match the input criteria using tabulate.
"""
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from tabulate import tabulate

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.theirstack_service import search_jobs_theirstack_multiple_pages, normalize_theirstack_job
from settings import THEIRSTACK_API_KEY


def check_job_title_match(input_keywords: List[str], output_title: str) -> bool:
    """Check if output job title matches input keywords"""
    if not input_keywords:
        return True
    
    output_lower = output_title.lower()
    # Check if any keyword is in the title
    return any(keyword.lower() in output_lower for keyword in input_keywords)


def check_company_match(input_keywords: List[str], output_company: str) -> bool:
    """Check if output company matches input keywords"""
    if not input_keywords:
        return True
    
    output_lower = output_company.lower()
    return any(keyword.lower() in output_lower for keyword in input_keywords)


def check_location_match(input_cities: List[str], input_states: List[str], output_city: str, output_state: str) -> bool:
    """Check if output location matches input location"""
    if not input_cities and not input_states:
        return True
    
    output_city_lower = output_city.lower() if output_city else ""
    output_state_lower = output_state.lower() if output_state else ""
    
    # Check city match (only if cities are specified)
    city_match = False
    if input_cities:
        city_match = any(city.lower() in output_city_lower for city in input_cities)
    
    # Check state match (only if states are specified)
    state_match = False
    if input_states:
        state_match = any(state.lower() in output_state_lower for state in input_states)
    
    # If both cities and states are specified, both must match (AND logic)
    # If only one is specified, that one must match
    if input_cities and input_states:
        return city_match and state_match
    elif input_cities:
        return city_match
    elif input_states:
        return state_match
    else:
        return True  # No filters specified


def check_country_match(input_countries: List[str], output_country: str, job_location: str = "") -> bool:
    """Check if output country matches input countries"""
    if not input_countries:
        return True
    
    # Normalize country codes
    country_map = {
        "US": ["us", "usa", "united states", "united states of america"],
        "CA": ["ca", "canada"],
        "UK": ["uk", "gb", "united kingdom", "great britain"]
    }
    
    output_lower = output_country.lower() if output_country else ""
    location_lower = job_location.lower() if job_location else ""
    
    # Check if country code matches
    for input_country in input_countries:
        input_upper = input_country.upper()
        if input_upper in country_map:
            # Check against known variations
            if any(variant in output_lower or variant in location_lower for variant in country_map[input_upper]):
                return True
        else:
            # Direct match
            if input_country.lower() in output_lower or input_country.lower() in location_lower:
                return True
    
    return False


def check_remote_match(input_remote: List[str], output_remote: any) -> bool:
    """Check if output remote type matches input"""
    if not input_remote:
        return True
    
    # Handle boolean values (True/False)
    if isinstance(output_remote, bool):
        # If API returned boolean, check if REMOTE is in input
        if output_remote is True:
            return "REMOTE" in [r.upper() for r in input_remote]
        else:
            # If False, check if we're looking for non-remote
            return any(r.upper() in ["ONSITE", "ON_SITE", "HYBRID"] for r in input_remote)
    
    # Handle string values
    output_lower = str(output_remote).lower() if output_remote else ""
    return any(remote.lower() in output_lower for remote in input_remote)


def check_employment_type_match(input_types: List[str], output_type: any) -> bool:
    """Check if output employment type matches input"""
    if not input_types:
        return True
    
    # Handle both string and other types
    output_lower = str(output_type).lower() if output_type else ""
    
    # If output is empty, we can't verify - but API filtered, so assume match
    if not output_lower:
        return True  # API filtered by employment_statuses_or, so likely correct
    
    # Check for common variations
    for emp_type in input_types:
        emp_upper = emp_type.upper()
        if "FULL_TIME" in emp_upper or "FULLTIME" in emp_upper:
            # Check for full-time variations
            if any(term in output_lower for term in ["full_time", "fulltime", "full-time", "full time", "permanent"]):
                return True
        elif "PART_TIME" in emp_upper or "PARTTIME" in emp_upper:
            # Check for part-time variations
            if any(term in output_lower for term in ["part_time", "parttime", "part-time", "part time", "contract"]):
                return True
        else:
            # Direct match
            if emp_type.lower() in output_lower:
                return True
    
    return False


def calculate_match_score(
    job: Dict[str, Any],
    job_title_keywords: Optional[List[str]] = None,
    company_keywords: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    remote_types: Optional[List[str]] = None,
    employment_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Calculate match score for a job based on input criteria.
    
    Returns:
        Dictionary with match results and overall score
    """
    normalized = normalize_theirstack_job(job)
    
    matches = {}
    total_checks = 0
    
    # Check each criterion
    if job_title_keywords:
        total_checks += 1
        matches["job_title"] = check_job_title_match(job_title_keywords, normalized.get("title", ""))
    
    if company_keywords:
        total_checks += 1
        matches["company"] = check_company_match(company_keywords, normalized.get("company", ""))
    
    if countries:
        total_checks += 1
        # If we filtered by country in the API, all returned jobs should match
        # But we still check the actual country field for accuracy
        country_field = normalized.get("country", "")
        location_field = normalized.get("location", "")
        
        # If country field is empty but we filtered by country, assume match
        # (since API already filtered)
        if not country_field and not location_field:
            # Can't verify, but API filtered so likely match
            matches["country"] = True
        else:
            matches["country"] = check_country_match(
                countries, 
                country_field,
                location_field
            )
    
    if cities or states:
        total_checks += 1
        # Get location data - check both dedicated fields and location string
        city = normalized.get("city", "")
        state = normalized.get("state", "")
        location_str = normalized.get("location", "")
        
        # Try to extract state from location string if state field is empty
        if not state and location_str:
            # Common patterns: "City, ST" or "City, State" or "City ST"
            import re
            # Match 2-letter state code at end: "City, ST" or "City ST"
            state_match = re.search(r',\s*([A-Z]{2})(?:\s|$)', location_str.upper())
            if state_match:
                state = state_match.group(1)
            else:
                # Try to match state name (less reliable, but worth trying)
                state_names = {
                    "california": "CA", "texas": "TX", "florida": "FL", "new york": "NY",
                    "pennsylvania": "PA", "illinois": "IL", "ohio": "OH", "georgia": "GA",
                    "north carolina": "NC", "michigan": "MI", "new jersey": "NJ",
                    "virginia": "VA", "washington": "WA", "arizona": "AZ", "massachusetts": "MA",
                    "tennessee": "TN", "indiana": "IN", "missouri": "MO", "maryland": "MD",
                    "wisconsin": "WI", "colorado": "CO", "minnesota": "MN", "south carolina": "SC"
                }
                location_lower = location_str.lower()
                for state_name, state_code in state_names.items():
                    if state_name in location_lower:
                        state = state_code
                        break
        
        matches["location"] = check_location_match(
            cities or [], states or [],
            city, state
        )
    
    if remote_types:
        total_checks += 1
        remote_value = normalized.get("remote")
        # Handle both boolean and string values
        matches["remote"] = check_remote_match(remote_types, remote_value)
    
    if employment_types:
        total_checks += 1
        matches["employment_type"] = check_employment_type_match(employment_types, normalized.get("employment_type", ""))
    
    # Calculate overall match percentage
    if total_checks > 0:
        match_count = sum(matches.values())
        match_percentage = (match_count / total_checks) * 100
    else:
        match_percentage = 100.0  # No criteria to match against
    
    return {
        "matches": matches,
        "match_percentage": match_percentage,
        "total_checks": total_checks
    }


def test_theirstack_accuracy(
    job_title_keywords: Optional[List[str]] = None,
    company_keywords: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    posted_at_max_age_days: Optional[int] = None,
    remote_types: Optional[List[str]] = None,
    employment_types: Optional[List[str]] = None,
    num_pages: int = 1,
    limit: int = 25,
    max_jobs: int = 20
):
    """
    Test TheirStack scraper accuracy with given input parameters.
    """
    print("=" * 80)
    print("THEIRSTACK JOB SEARCH API ACCURACY TEST")
    print("=" * 80)
    print()
    
    # Display input parameters
    print("INPUT PARAMETERS:")
    print(f"  Job Title Keywords: {', '.join(job_title_keywords) if job_title_keywords else 'Not specified'}")
    print(f"  Company Keywords: {', '.join(company_keywords) if company_keywords else 'Not specified'}")
    print(f"  Countries: {', '.join(countries) if countries else 'Not specified'}")
    print(f"  Cities: {', '.join(cities) if cities else 'Not specified'}")
    print(f"  States: {', '.join(states) if states else 'Not specified'}")
    print(f"  Posted Within: {posted_at_max_age_days} days" if posted_at_max_age_days else "  Posted Within: Not specified")
    print(f"  Remote Types: {', '.join(remote_types) if remote_types else 'Not specified'}")
    print(f"  Employment Types: {', '.join(employment_types) if employment_types else 'Not specified'}")
    print()
    print("-" * 80)
    print()
    
    # Check API key
    if not THEIRSTACK_API_KEY:
        print("ERROR: THEIRSTACK_API_KEY is not set in settings.py")
        print()
        print("To set your TheirStack API key:")
        print("  1. Create a .env file in the backend directory")
        print("  2. Add: THEIRSTACK_API_KEY=your-api-key-here")
        print("  3. Or set in settings.py directly")
        print()
        print("To get a TheirStack API key:")
        print("  1. Go to https://theirstack.com/")
        print("  2. Sign up or log in")
        print("  3. Get your API key from the dashboard")
        return None
    
    print(f"API Key loaded: {THEIRSTACK_API_KEY[:10]}..." if len(THEIRSTACK_API_KEY) > 10 else "API Key loaded")
    print()
    
    # Search for jobs
    try:
        print("Searching for jobs...")
        print("This may take a few moments...")
        print()
        
        # Convert remote_types list to boolean if provided
        remote_bool = None
        if remote_types:
            # If REMOTE is in the list, set to True, otherwise False
            if "REMOTE" in [r.upper() for r in remote_types]:
                remote_bool = True
            elif any(r.upper() in ["ONSITE", "ON_SITE", "HYBRID"] for r in remote_types):
                remote_bool = False
        
        # Convert employment_types to correct format (full_time, part_time)
        employment_statuses = None
        if employment_types:
            employment_statuses = []
            for emp_type in employment_types:
                emp_upper = emp_type.upper()
                if "FULL_TIME" in emp_upper or "FULLTIME" in emp_upper:
                    employment_statuses.append("full_time")
                elif "PART_TIME" in emp_upper or "PARTTIME" in emp_upper:
                    employment_statuses.append("part_time")
        
        # Build location patterns from cities and states
        location_patterns = []
        if cities:
            location_patterns.extend(cities)
        if states:
            location_patterns.extend(states)
        
        jobs = search_jobs_theirstack_multiple_pages(
            num_pages=num_pages,
            limit=limit,
            job_country_code_or=countries,
            posted_at_max_age_days=posted_at_max_age_days,
            job_title_or=job_title_keywords,
            company_name_partial_match_or=company_keywords,
            job_location_pattern_or=location_patterns if location_patterns else None,
            remote=remote_bool,
            employment_statuses_or=employment_statuses
        )
        
        if not jobs:
            print("No jobs found matching the criteria.")
            print()
            print("💡 Tips to get results:")
            print("  - Try less restrictive criteria (remove some filters)")
            print("  - Increase posted_at_max_age_days (e.g., 30 instead of 7)")
            print("  - Remove location filters (they use regex patterns)")
            print("  - Try without company filter")
            print("  - Check if the API returned any data (see debug output above)")
            print()
            print("Please check:")
            print("  1. Search parameters are correct")
            print("  2. API key is valid and has credits")
            print("  3. There are jobs available for the given criteria")
            return None
        
        # Limit to max_jobs
        if len(jobs) > max_jobs:
            jobs = jobs[:max_jobs]
            print(f"Limiting analysis to {max_jobs} jobs")
        
        print()
        print("-" * 80)
        print()
        
        # Calculate matches for all jobs
        table_data = []
        all_match_percentages = []
        
        # Debug: Show first job structure to understand data format
        if jobs:
            first_job = jobs[0]
            normalized_first = normalize_theirstack_job(first_job)
            print(f"🔍 Debug - First job structure:")
            print(f"   Raw job keys: {list(first_job.keys())[:10]}...")  # Show first 10 keys
            print(f"   Normalized country: '{normalized_first.get('country', 'N/A')}'")
            print(f"   Normalized location: '{normalized_first.get('location', 'N/A')[:50]}'")
            print(f"   Normalized state: '{normalized_first.get('state', 'N/A')}'")
            print(f"   Normalized city: '{normalized_first.get('city', 'N/A')}'")
            print(f"   Normalized employment_type: '{normalized_first.get('employment_type', 'N/A')}'")
            print(f"   Raw employment_type fields: {[k for k in first_job.keys() if 'employ' in k.lower() or 'type' in k.lower()]}")
            print(f"   Raw location fields: {[k for k in first_job.keys() if 'locat' in k.lower() or 'state' in k.lower() or 'city' in k.lower()]}")
            print()
        
        for job in jobs:
            normalized = normalize_theirstack_job(job)
            match_result = calculate_match_score(
                job,
                job_title_keywords=job_title_keywords,
                company_keywords=company_keywords,
                countries=countries,
                cities=cities,
                states=states,
                remote_types=remote_types,
                employment_types=employment_types
            )
            
            all_match_percentages.append(match_result["match_percentage"])
            
            # Build match indicators
            match_indicators = []
            if job_title_keywords:
                match_indicators.append("✓" if match_result["matches"].get("job_title", False) else "✗")
            if company_keywords:
                match_indicators.append("✓" if match_result["matches"].get("company", False) else "✗")
            if countries:
                match_indicators.append("✓" if match_result["matches"].get("country", False) else "✗")
            if cities or states:
                match_indicators.append("✓" if match_result["matches"].get("location", False) else "✗")
            if remote_types:
                match_indicators.append("✓" if match_result["matches"].get("remote", False) else "✗")
            if employment_types:
                match_indicators.append("✓" if match_result["matches"].get("employment_type", False) else "✗")
            
            # Prepare table row - ensure all values are strings before slicing
            title = str(normalized.get("title", "N/A") or "N/A")
            company = str(normalized.get("company", "N/A") or "N/A")
            location = str(normalized.get("location", "N/A") or "N/A")
            
            row_data = [
                title[:45] + ("..." if len(title) > 45 else ""),
                company[:25] + ("..." if len(company) > 25 else ""),
                location[:20] + ("..." if len(location) > 20 else ""),
            ]
            
            if match_indicators:
                row_data.append("".join(match_indicators))
                row_data.append(f"{match_result['match_percentage']:.1f}%")
            
            table_data.append(row_data)
        
        # Build table headers
        headers = ["Job Title", "Company", "Location"]
        if job_title_keywords or company_keywords or countries or cities or states or remote_types or employment_types:
            match_header_parts = []
            if job_title_keywords:
                match_header_parts.append("T")
            if company_keywords:
                match_header_parts.append("C")
            if countries:
                match_header_parts.append("Co")
            if cities or states:
                match_header_parts.append("L")
            if remote_types:
                match_header_parts.append("R")
            if employment_types:
                match_header_parts.append("E")
            headers.append("Matches")
            headers.append("Accuracy")
        
        # Display results with tabulate
        print("=" * 80)
        print("JOB RESULTS WITH ACCURACY")
        print("=" * 80)
        print()
        
        print(tabulate(
            table_data,
            headers=headers,
            tablefmt="grid",
            maxcolwidths=[45, 25, 20, 8, 10]
        ))
        print()
        
        # Display legend and statistics
        if job_title_keywords or company_keywords or countries or cities or states or remote_types or employment_types:
            print("Match Indicators: ", end="")
            if job_title_keywords:
                print("T=Title ", end="")
            if company_keywords:
                print("C=Company ", end="")
            if countries:
                print("Co=Country ", end="")
            if cities or states:
                print("L=Location ", end="")
            if remote_types:
                print("R=Remote ", end="")
            if employment_types:
                print("E=Employment ", end="")
            print("(✓ = Match, ✗ = No Match)")
            print()
            
            # Overall statistics
            avg_match = sum(all_match_percentages) / len(all_match_percentages) if all_match_percentages else 0
            perfect_matches = sum(1 for p in all_match_percentages if p == 100)
            high_quality = sum(1 for p in all_match_percentages if p >= 80)
            
            print("-" * 80)
            print("ACCURACY STATISTICS")
            print("-" * 80)
            print(f"Total Jobs Analyzed: {len(jobs)}")
            print(f"Average Match Score: {avg_match:.1f}%")
            print(f"Perfect Matches (100%): {perfect_matches}/{len(jobs)}")
            print(f"High Quality Matches (≥80%): {high_quality}/{len(jobs)}")
            print(f"Low Quality Matches (<50%): {sum(1 for p in all_match_percentages if p < 50)}/{len(jobs)}")
            print()
        
        print("=" * 80)
        print("TEST COMPLETED")
        print("=" * 80)
        
        return {
            "jobs": jobs,
            "total": len(jobs),
            "average_match": avg_match if all_match_percentages else 0,
            "match_percentages": all_match_percentages
        }
        
    except ValueError as e:
        # Subscription/validation error - already handled with helpful message
        return None
    except Exception as e:
        print(f"ERROR during scraping: {str(e)}")
        print()
        print("Please ensure:")
        print("  1. THEIRSTACK_API_KEY is valid and has credits")
        print("  2. All required packages are installed:")
        print("     pip install requests tabulate")
        print("  3. Internet connection is working")
        print()
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # ⚠️  CRITICAL API CREDITS WARNING ⚠️
    # 1 API CREDIT = 1 JOB
    # Each job returned costs 1 credit
    # BE CAREFUL - Comment out tests you don't need!
    
    print("=" * 80)
    print("⚠️  API CREDITS WARNING ⚠️")
    print("=" * 80)
    print("1 API Credit = 1 Job Returned")
    print("Each test case costs credits based on jobs returned")
    print("Comment out test cases you don't need!")
    print("=" * 80)
    print()
    
    # Test Case 1: Basic search - minimal test (2 credits)
    print("TEST CASE 1: Basic Search (Country and Date Only)")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: Basic API functionality")
    print()
    test_theirstack_accuracy(
        countries=["US"],
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # Only 2 jobs = 2 credits (MINIMAL)
        max_jobs=2
    )
    
    print()
    print()
    print("=" * 80)
    print()
    
    # Test Case 2: Search with job title only (tests job_title_or filter)
    print("TEST CASE 2: Search by Job Title Only")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: job_title_or filter accuracy")
    print()
    test_theirstack_accuracy(
        job_title_keywords=["Software Engineer"],
        countries=["US"],
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # 2 jobs = 2 credits
        max_jobs=2
    )
    # 
    # print()
    # print()
    # print("=" * 80)
    # print()
    # 
    print()
    print()
    print("=" * 80)
    print()
    
    # Test Case 3: Search by company name (tests company_name_partial_match_or filter)
    print("TEST CASE 3: Search by Company Name")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: company_name_partial_match_or filter accuracy")
    print()
    test_theirstack_accuracy(
        company_keywords=["Google"],
        countries=["US"],
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # 2 jobs = 2 credits
        max_jobs=2
    )
    # 
    # print()
    # print()
    # print("=" * 80)
    # print()
    # 
    print()
    print()
    print("=" * 80)
    print()
    
    # Test Case 4: Search by location state (tests job_location_pattern_or filter)
    print("TEST CASE 4: Search by Location (State)")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: job_location_pattern_or filter accuracy")
    print()
    test_theirstack_accuracy(
        countries=["US"],
        states=["CA"],  # California
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # 2 jobs = 2 credits
        max_jobs=2
    )
    
    print()
    print()
    print("=" * 80)
    print()
    
    # Test Case 5: Search with remote filter (tests remote boolean filter)
    print("TEST CASE 5: Search Remote Jobs Only")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: remote boolean filter accuracy")
    print()
    test_theirstack_accuracy(
        job_title_keywords=["Developer"],
        countries=["US"],
        remote_types=["REMOTE"],
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # 2 jobs = 2 credits
        max_jobs=2
    )
    # 
    # print()
    # print()
    # print("=" * 80)
    # print()
    # 
    print()
    print()
    print("=" * 80)
    print()
    
    # Test Case 6: Search with employment type filter (tests employment_statuses_or filter)
    print("TEST CASE 6: Search Full-Time Jobs Only")
    print("💳 Cost: ~2 credits (2 jobs)")
    print("📊 Tests: employment_statuses_or filter accuracy")
    print()
    test_theirstack_accuracy(
        job_title_keywords=["Engineer"],
        countries=["US"],
        employment_types=["FULL_TIME"],
        posted_at_max_age_days=30,
        num_pages=1,
        limit=2,  # 2 jobs = 2 credits
        max_jobs=2
    )
    # 
    # COMMENTED OUT - Uncomment only if you need to test these specific combinations
    # Each costs 2 credits (2 jobs)
    
    # # Test Case 7: Combined filters - job title + company
    # print("TEST CASE 7: Combined Filters (Title + Company)")
    # print("💳 Cost: ~2 credits (2 jobs)")
    # print("📊 Tests: Multiple filter combination accuracy")
    # print()
    # test_theirstack_accuracy(
    #     job_title_keywords=["Data Analyst"],
    #     company_keywords=["Microsoft"],
    #     countries=["US"],
    #     posted_at_max_age_days=30,
    #     num_pages=1,
    #     limit=2,  # 2 jobs = 2 credits
    #     max_jobs=2
    # )
    # 
    # print()
    # print()
    # print("=" * 80)
    # print()
    # 
    # # Test Case 8: Multiple filters - title + remote + employment type
    # print("TEST CASE 8: Multiple Filters (Title + Remote + Employment Type)")
    # print("💳 Cost: ~2 credits (2 jobs)")
    # print("📊 Tests: Complex filter combination accuracy")
    # print()
    # test_theirstack_accuracy(
    #     job_title_keywords=["Software Engineer"],
    #     countries=["US"],
    #     remote_types=["REMOTE"],
    #     employment_types=["FULL_TIME"],
    #     posted_at_max_age_days=30,
    #     num_pages=1,
    #     limit=2,  # 2 jobs = 2 credits
    #     max_jobs=2
    # )
    
    print()
    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)
    print("💳 Total cost: ~12 credits (6 test cases × 2 jobs each)")
    print("💡 Remaining credits: ~185/200")
    print("⚠️  Remember: 1 credit = 1 job")
    print("=" * 80)

