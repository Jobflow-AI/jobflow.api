from function.utils import createFile, fetch_job_details_linkedin, extract_salary
from function.insert_job import insert_job
from function.utils import extract_salary
import re
from function.aiHelper import extract_job_details_with_AI
import requests
from bs4 import BeautifulSoup
import urllib
import time
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def extract_job_id(job_link):
    match = re.search(r'-(\d+)\?', job_link)
    return match.group(1) if match else None

def fetch_jobs_from_api(base_url, headers, start, count):
    """Fetch jobs from LinkedIn API with pagination."""
    params = {
        'f_TPR': 'r3000',
        'geoId': '102713980',
        'sortBy': 'DD',
        'f_E': '1,2,3',
        'start': start,
    }

    finalUrl = base_url + "?" + urllib.parse.urlencode(params)
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print(f"Failed to fetch jobs at start={start}: {response.status_code}, error: {response}")
        return None

async def scrape_linkedin_jobs(soup, portal='linkedin', portal_logo='https://www.linkedin.com/favicon.ico'):
    """Process job listings from BeautifulSoup object."""
    jobs = soup.find_all('li')
    job_count = 0

    for job in jobs:
        title = job.find('h3', class_='base-search-card__title')
        company_name = job.find('h4', class_='base-search-card__subtitle')
        if title and company_name:
            job_link = job.find('a', class_='base-card__full-link')
            job_link = job_link['href'].strip() if job_link else None
            job_id = extract_job_id(job_link)


            job_location = job.find('span', class_='job-search-card__location')
            if job_link:
                job_details = fetch_job_details_linkedin(job_link)
                if job_details:
                    job_salary, experience_level, job_type, job_description, company_legit_check = job_details
                    if company_legit_check is None:
                        logger.info(f"Skipping this job: {title.text.strip()}, Company: {company_name.text.strip()}")
                        continue
                else:
                    logger.info(f"No job details found for: {title.text.strip()}, Company: {company_name.text.strip()}")
                    continue
            else:
                logger.info(f"Skipping job with no link: {title.text.strip()}, Company: {company_name.text.strip()}")
                continue
            job_count += 1

            jd_extracted = extract_job_details_with_AI(job_description)
            company_logo_element = job.find('div', class_='search-entity-media')
            company_logo=None
            if company_logo_element:
                img_tag= company_logo_element.find('img')
                if img_tag: 
                    company_logo = img_tag['data-delayed-url']

            salary_min = None
            salary_max = None
            end_date = None

            if job_salary:
                salary_min, salary_max = extract_salary(job_salary)  
            
            if jd_extracted:
                if salary_min is None:
                    salary_min = jd_extracted.get("salary_min")
                if salary_max is None:
                    salary_max = jd_extracted.get("salary_max")
                if job_salary is None:
                    job_salary = jd_extracted.get("job_salary")
                if jd_extracted.get("end_date"):
                    end_date = jd_extracted.get("end_date")

            if title and company_name and job_link and job_location:
                job_info = {
                    "title": title.text.strip(),
                    "company_name": company_name.text.strip(),
                    "company_logo": company_logo,
                    "job_link": job_link,
                    "job_id": job_id,
                    "job_location": job_location.text.strip(),
                    "job_type": job_type,
                    "job_salary": job_salary,
                    "salary_min": salary_min ,
                    "salary_max": salary_max,
                    "experience_min": jd_extracted.get("experience_min"),
                    "experience_max": jd_extracted.get("experience_max"),
                    "experience": experience_level,
                    "skills_required": jd_extracted.get("skills_required"),
                    "job_description": job_description,
                    "end_date": end_date,
                    "source": portal,
                    "source_logo": portal_logo
                }
                try:
                    await insert_job(job_info)
                    # createFile(file, title.text.strip(), company_name.text.strip(), job_link, job_location.text.strip(), None, None, experience_level, job_salary, portal, job_type)
                except Exception as e:
                    print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
    return job_count

async def scrape_linkedin():
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    page_url = "https://www.linkedin.com/jobs/search/?keywords=&location=India&geoId=102713980&f_TPR=r3000&f_E=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        # 'Cookie': 'YOUR_LINKEDIN_COOKIE_HERE'
    }

    start = 25
    count = 25  
    total_jobs = 0
    requestCount = 0

    print("Starting LinkedIn job scraping...")

    # Initial Scraping
    response = requests.get(page_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    total_jobs += await scrape_linkedin_jobs(soup)
    requestCount += 1


    print(f"Fetched {total_jobs} jobs, total: {total_jobs}")
    while True:
        soup = fetch_jobs_from_api(base_url, headers, start, count)
        if not soup:
            break
        
        jobs_fetched = await scrape_linkedin_jobs(soup)
        total_jobs += jobs_fetched
        
        print(f"Fetched {jobs_fetched} jobs, total: {total_jobs}")
        if jobs_fetched == 0:
            break
        
        start += count
        requestCount += 1
        if requestCount % 18 == 0:
            print("Fetched {jobs_fetched} jobs, total: {total_jobs}", "Wait for 10 seconds...")
            time.sleep(65)  # Small delay to avoid rate limiting
        
    print(f"Scraping complete. Total jobs fetched: {total_jobs}")





async def scrape_linkedin_jobpage(soup, job_link):
    portal = 'linkedin'
    
    if not soup:
        return None
    
    # Initialize job data dictionary with default values
    job_info = {
        "title": None,
        "job_link": job_link,
        "job_location": None,
        "company_name": None,
        "company_logo": None,
        "source": portal
    }
    
    try:
        # Extract job title
        title_element = soup.find('h3', class_="sub-nav-cta__header")
        if title_element:
            job_info["title"] = title_element.text.strip()
        
        # Extract company details and location
        job_title_element = soup.find('div', class_='sub-nav-cta__text-container')
        if job_title_element:
            company_element = job_title_element.find('a', class_="sub-nav-cta__optional-url")
            location_element = job_title_element.find('span')
            
            if company_element:
                job_info["company_name"] = company_element.text.strip()
            if location_element:
                job_info["job_location"] = location_element.text.strip()
        
        # Extract company logo
        company_logo_element = soup.find('div', class_='sub-nav-cta__content')
        if company_logo_element and (img_tag := company_logo_element.find('img')):
            job_info["company_logo"] = img_tag.get('data-delayed-url')
        
        # Validate required fields
        if not all([job_info["title"], job_info["company_name"]]):
            print(f"Warning: Missing required fields for job listing: {job_link}")
            
        return job_info
        
    except Exception as e:
        print(f"Error scraping LinkedIn job page: {str(e)}")
        return None