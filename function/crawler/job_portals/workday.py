import requests
import json
import time
import logging
from bs4 import BeautifulSoup
from function.aiHelper import extract_job_details_with_AI
from function.insert_job import insert_job
from db.prisma import db

# Configure minimal logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

CHECK_LIMIT = 4

COMPANY_URLS = [
    [
        "https://workday.wd5.myworkdayjobs.com/Workday?locations=91e43cc2ca1a01d1a4aa05e58d0e252b&locations=6052d74f129510015da0e00b75760000",
        "https://workday.wd5.myworkdayjobs.com/wday/cxs/workday/Workday",
    ],
    [
        "https://philips.wd3.myworkdayjobs.com/jobs-and-careers?locationHierarchy1=6e1b2a934716103c2adde1d57e7700ea",
        "https://philips.wd3.myworkdayjobs.com/wday/cxs/philips/jobs-and-careers"
    ]
    # Add other company URL lists here
]

def fetch_job_list(url, locationQuery=""):
    """Fetch the job list JSON from the Workday API with pagination."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "content-type": "application/json"
    }
    api_url = f"{url}/jobs"
    
    if locationQuery:
        locationParam = locationQuery.split("=")[0]
        location_values = [value.split("=")[1] for value in locationQuery.split("&") if value.startswith(locationParam)]
        base_payload = {
            "limit": 20,
            "appliedFacets": {
                locationParam: location_values
            }
        }
    else:
        base_payload = {"limit": 20}
    
    all_jobs = []
    offset = 0
    total_jobs = None  
    
    while True:
        payload = {**base_payload, "offset": offset}
        
        retries = 3
        success = False
        
        for attempt in range(retries):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                jobs = data.get('jobPostings', [])
                if jobs:
                    all_jobs.extend(jobs)
                
                if total_jobs is None:
                    total_jobs = data.get('total', 0)
                
                if not jobs:
                    return all_jobs
                
                if total_jobs and offset + len(jobs) >= total_jobs:
                    return all_jobs
                
                offset += len(jobs)
                success = True
                break
            except Exception as e:
                if attempt < retries - 1:
                    print(f"Attempt {attempt + 1} failed. Retrying...")
                    time.sleep(2)
                else:
                    print(f"Failed to fetch job list from {api_url} after {retries} attempts: {e}")
                    return all_jobs
        
        if not success:
            break
    
    return all_jobs

def scrape_workday_job_details(url, externalPath):
    """Fetch and process individual job details."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "content-type": "application/json"
    }
    try:
        api_url = f"{url}{externalPath}"
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        job_page_json = response.json()
        jobDetails = job_page_json.get("jobPostingInfo", {})

        # Source logo
        base_url = url.split('.com')[0] + '.com'
        favicon_url = f"{base_url}/favicon.ico"
        companyName = url.split("//")[1].split(".")[0]
        if(jobDetails.get("postedOn") == "Posted 30+ Days Ago"):
            return None
        
        # print(jobDetails.get("title", "N/A"))

        job_info = {
            "title": jobDetails.get("title", "N/A"),
            "job_link": jobDetails.get("externalUrl", None),
            "apply_link": jobDetails.get("externalUrl", None),
            # "job_id": jobDetails.get("id", None),
            "company_name": companyName,
            "company_logo": favicon_url,
            "job_location": jobDetails.get("location", {}),
            "job_type": jobDetails.get("timeType", "N/A"),
            "job_description": jobDetails.get("jobDescription", "N/A"),
            "source": "workday",
            "source_logo": None, 
            "posted": jobDetails.get("startDate", None),
            "end_date": jobDetails.get("endDate", None),
        }

        jd_html = job_info["job_description"]
        soup = BeautifulSoup(jd_html, 'html.parser')
        jd_text = soup.get_text(strip=True) 

        jd_extracted = extract_job_details_with_AI(jd_text)
        job_info.update({
            "salary_min": jd_extracted.get("salary_min"),
            "salary_max": jd_extracted.get("salary_max"),
            "job_salary": jd_extracted.get("job_salary"),
            "experience_min": jd_extracted.get("experience_min"),
            "experience_max": jd_extracted.get("experience_max"),
            "experience": jd_extracted.get("experience"),
            "skills_required": jd_extracted.get("skills_required"),
        })

        return job_info
    except Exception as e:
        # logger.error(f"Failed to scrape job details from {url}{externalPath}: {e}")
        print("Failed to scrape job details from", url, externalPath, e)
        return None

async def scrape_workday():
    """Main function to scrape Workday jobs."""
    portal = "workday"
    # logger.info(f"Starting scrape for {portal}...")
    print(f"Starting scrape for {portal}...")

    for url in COMPANY_URLS:
        company_name = url[0].split("//")[1].split(".")[0].lower()
        company_link = url[0].split("?")[0] if "?" in url[0] else url[0]
        locationQuery = url[0].split("?")[1] if "?" in url[0] else ""

        jobs = fetch_job_list(url[1], locationQuery)
        if not jobs:
            print("No jobs found")
            continue
        

        company = await db.company.find_unique(where={"company_name": company_name})
        if not company:
            company = await db.company.create(data={
                "company_name": company_name,
                "company_link": company_link,
                "last_job_ids": "[]"  
            })
        last_job_ids = set()
        if company.last_job_ids:
            try:
                try:
                    cleaned_json = json.dumps(company.last_job_ids)
                    parsed_ids = json.loads(cleaned_json)
                    last_job_ids = set(parsed_ids)
                except (AttributeError, json.JSONDecodeError) as e:
                    print(f"JSON parsing error: {str(e)}")
                    last_job_ids = set()
            except Exception as e:
                print(f"JSON parsing error: {str(e)}")
                last_job_ids = set()
        

        current_job_ids = []
        jobs_to_process = []
        dup_count = 0
        total_skipped = 0

        for job in jobs:
            job_id = job.get("bulletFields", [""])[0]
            externalPath = job.get("externalPath", None)

            if job_id in last_job_ids:
                dup_count += 1
                total_skipped += 1
                if dup_count >= CHECK_LIMIT:
                    print(f"Hit {CHECK_LIMIT} duplicates at {job_id}; skipping rest")
                    break
                continue

            dup_count = 0
            job_info = scrape_workday_job_details(url[1], externalPath)
            if job_info:
                current_job_ids.append(job_id)
                job_info["job_id"] = job_id
                jobs_to_process.append(job_info)   

        for job_info in jobs_to_process:
            try:
                await insert_job(job_info)
                # logger.info(f"Inserted job: {job_info['title']}")
                # print("Inserted job", job_info['title'])
            except Exception as e:
                # logger.error(f"Error inserting job {job_info['title']}: {e}")
                print("Error inserting job", job_info['title'], e)
        
        # Update last_job_ids
        updated_job_ids = list(last_job_ids.union(current_job_ids))
        company = await db.company.update(
            where={"company_name": company_name},
            data={"last_job_ids": json.dumps(updated_job_ids)}
        )
        print(f"Finished for {company_name}: Processed {len(jobs_to_process)} jobs")

        # Rate limiting
        time.sleep(1.5)  # 1-2s delay between requests
