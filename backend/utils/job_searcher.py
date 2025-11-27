import requests
import json
from typing import Any
from settings import RAPID_API_KEY

def search_jobs(keywords: list[str], num_pages: int = 1) -> list[dict[str, Any]]:
    """
    Searches for jobs using combined keywords via JSearch API.
    :param keywords: List of keywords to form the query.
    :param num_pages: Number of pages to fetch (default 1).
    :return: List of job results.
    """
    # Filter keywords to find job titles and remove special characters
    # Look for keywords that are likely job titles (usually 1-3 words, no special chars)
    job_keywords = [k for k in keywords if len(k.split()) <= 3 and '&' not in k and '$' not in k][:3]
    
    # If we found job keywords, use them; otherwise use the first few keywords
    if not job_keywords:
        job_keywords = [k for k in keywords if len(k) > 2][:3]
    
    if not job_keywords:
        job_keywords = keywords[:3]
    
    # Create a simple query from the best keywords
    query = ' '.join(job_keywords) if job_keywords else "sales"
    
    url = "https://jsearch.p.rapidapi.com/search"
    headers: dict[str, Any] = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    all_jobs: list[dict[str, Any]] = []
    
    print(f"Searching for jobs with query: {query}")
    
    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1"  # Fetch one page at a time
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            response_data = response.json()
            data: list[dict[str, Any]] = response_data.get('data', [])
            print(f"Page {page}: Found {len(data)} jobs")
            all_jobs.extend(data)
        else:
            print(f"Error fetching jobs on page {page}: {response.status_code}")
            print(f"Response: {response.text}")
    
    print(f"Total jobs found: {len(all_jobs)}")
    return all_jobs

def save_jobs_to_json(jobs: list[dict[str, Any]], output_path: str = 'output/jobs.json') -> None:
    """
    Saves job results to a JSON file.
    """
    with open(output_path, 'w') as f:
        json.dump(jobs, f, indent=4)
    print(f"Jobs saved to {output_path}")