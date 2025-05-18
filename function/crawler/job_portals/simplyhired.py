from function.utils import createFile
from function.insert_job import insert_job
from function.utils import extract_salary
from dotenv import load_dotenv
import os
import logging
import requests
from bs4 import BeautifulSoup
import urllib
import time
from db.prisma import db
from function.aiHelper import extract_job_details_with_AI

from datetime import timedelta, datetime


logging.basicConfig(filename= 'log.txt',  level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

scraperapi_key = os.getenv('SCRAPER_API')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

async def scrape_simplyhired_jobpage(soup):
    portal = 'simplyhired'
    print("inside simplyhired scrape \n")
    jobs_count = 0
    job_list = soup.find('ul', id='job-list')
    if job_list:
        jobs = job_list.find_all('li')
        # with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
        for job in jobs:
            # print(job)
            title_element = job.find('a', class_='chakra-button css-1djbb1k')
            title = title_element.text.strip() if title_element else None
            if title is None:
                continue
            company_name_element = job.find('span', class_='css-lvyu5j').find('span')
            company_name = company_name_element.text.strip() if company_name_element else None
                            
            if company_name:
                normalized_company_name = company_name.strip().lower()
                company = await db.company.find_unique(where={'company_name': normalized_company_name})
                
                if company and title:
                    existing_job = await db.job.find_first(where={
                        "title": title,
                        "companyId": company.id,
                        "status": "active"
                    })
                        
                    if existing_job:
                        logger.info(f"Job '{title}' already exists for company '{company_name}'")
                        continue 
            if not company_name:
                company_name = "Unknown Company"

            logger.info(f"Title: {title}, Company Name: {company_name}")
            jobs_count += 1

            job_link_element = title_element['href']
            job_location_element = job.find('span', class_='css-1t92pv')
            job_salary_element = job.find('p', class_='chakra-text css-1g1y608')
            job_link = "https://www.simplyhired.co.in" + job_link_element if job_link_element else None
            job_location = job_location_element.text.strip() if job_location_element else None
            job_salary = job_salary_element.text.strip() if job_salary_element else None

            salary_min = None
            salary_max = None

            if job_salary:
                salary_min, salary_max = extract_salary(job_salary)  
            
            job_description, job_type, posted, skills_required, company_logo_url = fetch_job_details_simplyhired(job_link)

            time.sleep(1)
            jd_extracted = extract_job_details_with_AI(job_description)
            
            experience_min = jd_extracted['experience_min']
            experience_max = jd_extracted['experience_max']
            experience = jd_extracted['experience']
            end_date = jd_extracted['end_date']

            job_info = {
                "title": title,
                "company_name": company_name,
                "company_logo": company_logo_url,
                "job_link": job_link,
                "job_location": job_location,
                "job_salary": job_salary,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "job_description": job_description,
                "job_type": job_type,
                "posted": posted,
                "skills_required": skills_required,
                "experience_min": experience_min,
                "experience_max": experience_max,
                "experience": experience,
                "end_date": end_date,
                "source": portal
            }
            try:    
                # print(job_info)
                await insert_job(job_info)   
            except Exception as e:
                print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
    return jobs_count


def fetch_job_details_simplyhired(job_url):
    try:
        proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={job_url}"
        response = requests.get(proxy_url, headers=headers)
        response.raise_for_status()
        job_page = BeautifulSoup(response.text, 'html.parser')

        # Company Logo
        company_logo = job_page.find('img', {'data-testid': 'companyVJLogo'})
        company_logo_url = company_logo['src'] if company_logo else None

        # Job Type
        job_type_div = job_page.find('div', {'data-testid': 'viewJobBodyJobDetailsContainer'})
        job_type = job_type_div.find('span', {'data-testid': 'detailText'}).text

        # Posted TimeStamp
        posted = None
        # timestamp_span = job_page.find('span', {'data-testid': 'viewJobBodyJobPostingTimestamp'})
        # if timestamp_span:
        #     posted_str = timestamp_span.find('span', {'data-testid': 'detailText'}).text.strip()
        #     try:
        #         posted = datetime.strptime(posted_str, "%Y-%m-%d")
        #     except ValueError:
        #         if 'hours ago' in posted_str:
        #             hours = int(posted_str.split()[0])
        #             posted = datetime.now() - timedelta(hours=hours)
        
        # Skills Required
        qualifications_container = job_page.find('div', {'data-testid': 'viewJobQualificationsContainer'})
        qualification_items = qualifications_container.find_all('span', {'data-testid': 'viewJobQualificationItem'})
        skills_required = [item.text for item in qualification_items]

        # Job Description
        job_description = job_page.find('div', {'data-testid': 'viewJobBodyJobFullDescriptionContent'})
        job_description = job_description.text.strip() if job_description else None

        return job_description, job_type, posted, skills_required, company_logo_url

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch salary from {job_url}: {e}")
        return None


searchKeywords = [
    "software developer",
    "data scientist",
    "full stack developer",
    "python developer",
    "project manager",
    "machine learning engineer",
    "data analyst",
    "cloud engineer",
    "frontend developer",
    "backend developer",
    "product manager",
    "devops engineer",
    "HR manager",
    "digital marketing",
    "business analyst",
    "sales manager",
    "AI research scientist",
    "web developer",
    "graphic designer",
    "react developer"
]

async def scrape_simplyhired():
    total_jobs = 0
    logger.info("Starting to scrape SimplyHired")
    for keyword in searchKeywords:
        keyword_hyphenated = keyword.replace(" ", "+")
        base_url = "https://www.simplyhired.co.in/search"
        currentJobs = 0
        for job_type in ["CF3CP", "VDTG7"]:
            params = {
                "q": keyword_hyphenated,
                "l": "india",
                "t": "1",
                "jt": job_type
            }
            if job_type == "CF3CP":
                params["mip"] = "830000"

            # Get first page
            url = base_url + "?" + "&".join(f"{k}={v}" for k, v in params.items())
            page_count = 1
            
            while True:
                try:
                    logger.info(f"Processing page {page_count} for {keyword} ({'Full Time' if job_type == 'CF3CP' else 'Internship'})")
                    proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={url}"
                    response = requests.get(proxy_url, headers=headers)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    logger.info(f"Scraping page {page_count} for {keyword} ({'Full Time' if job_type == 'CF3CP' else 'Internship'})")
                    
                    currentJobs += await scrape_simplyhired_jobpage(soup)
                    print(f"Jobs fetched: {currentJobs} for {keyword} jobs on page {page_count}")
                    
                    pagination = soup.find('nav', {'data-testid': 'pageNumberContainer'})
                    if not pagination:
                        break
                        
                    next_page = pagination.find('a', {'data-testid': f'paginationBlock{page_count + 1}'})
                    if not next_page or page_count >= 10:  # Limit to 10 pages
                        break
                        
                    url = next_page['href']
                    page_count += 1
                    # time.sleep(1) 
                    
                except Exception as e:
                    print(f"Error on page {page_count}: {str(e)}")
                    break
        total_jobs += currentJobs
        print(f"Jobs fetched: {total_jobs} for {keyword} jobs")
        
