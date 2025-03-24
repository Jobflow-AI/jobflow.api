from function.utils import createFile, fetch_job_details_linkedin, extract_salary
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


logging.basicConfig(filename= 'log.txt',  level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

scraperapi_key = os.getenv('SCRAPER_API')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

async def scrape_glassdoor_jobpage(soup):
    portal = 'glassdoor'
    print("inside glassdoor scrape \n")
    job_list = soup.find('ul', class_='JobsList_jobsList__lqjTr')
    jobs_count = 0
    if job_list:
        jobs = job_list.find_all('li')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title_element = job.find('a', class_='JobCard_jobTitle__GLyJ1')
                title = title_element.text.strip() if title_element else None
                if title is None:
                    continue
                company_name_element = job.find('span', class_='EmployerProfile_compactEmployerName__9MGcV')
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
                job_link = title_element['href'] if title_element else None
                job_location_element = job.find('div', class_='JobCard_location__Ds1fM')
                job_location = job_location_element.text.strip() if job_location_element else None
                job_salary_element = job.find('div', class_='JobCard_salaryEstimate__QpbTW')
                job_salary = job_salary_element.text.strip() if job_salary_element else None

                logo_tag = job.find('img', class_='avatar-base_Image__2RcF9')
                logo_url = None
                if logo_tag and 'src' in logo_tag.attrs:
                    logo_url = logo_tag['src']

                company_logo = logo_url

                time.sleep(2)
                job_description = fetch_job_details_glassdoor(job_link)
                job_description = job_description.get_text(strip=True)

                jd_extracted = extract_job_details_with_AI(job_description)
                
                skills = jd_extracted['skills_required']
                experience_min = jd_extracted['experience_min']
                experience_max = jd_extracted['experience_max']
                experience = jd_extracted['experience']
                end_date = jd_extracted['end_date']
                job_type = jd_extracted['job_type']


                salary_min = None
                salary_max = None

                if job_salary:
                    salary_min, salary_max = extract_salary(job_salary)  

                if title and company_name and job_link and job_location:
                    job_info = {
                        "title": title,
                        "company_name": company_name,
                        "company_logo": company_logo,
                        "job_link": job_link,
                        "job_location": job_location,
                        "job_salary": job_salary,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "skills_required": skills,
                        "experience_level": experience,
                        "experience_min": experience_min,
                        "experience_max": experience_max,
                        "end_date": end_date,
                        "job_type": job_type,
                        "job_description": job_description,
                        "source": portal
                    }
                    try:
                        await insert_job(job_info)
                        # createFile(file, title, company_name, job_link, job_location, job_description, skills, None, job_salary, portal, None)
                    except Exception as e:
                        print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
    return jobs_count

def fetch_job_details_glassdoor(job_url):
    try:
        proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={job_url}"
        response = requests.get(proxy_url, headers=headers)
        response.raise_for_status()
        job_page = BeautifulSoup(response.text, 'html.parser')

        job_description = job_page.find('div', class_=lambda x: x and 'JobDetails_jobDescription__uW_fK' in x)
        return job_description

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

async def scrape_glassdoor():
    total_jobs = 0
    
    for keyword in searchKeywords:
        keyword_hyphenated = keyword.replace(" ", "-")
        ko_end = 6 + len(keyword_hyphenated) + 1  
        base_url = "https://www.glassdoor.co.in/Job/india-{keyword}-jobs-SRCH_IL.0,5_IN115_KO6,{ko_end}.htm"
        seniority_types = ["entrylevel", "internship"]
        currentJobs = 0
        for seniority in seniority_types:
            params = {
                "maxSalary": 6000000,
                "minSalary": 10000,
                "fromAge": 1,
                "sortBy": "date_desc",
                "seniorityType": seniority
            }
            url = base_url.format(keyword=keyword_hyphenated, ko_end=ko_end)
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

            proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={url}"
            response = requests.get(proxy_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"URL for {seniority}: {url}")
            time.sleep(2)
            currentJobs += await scrape_glassdoor_jobpage(soup)
        total_jobs += currentJobs
        print(f"Jobs fetched: {currentJobs} for {keyword} jobs")
        
    print(f"Total jobs fetched: {total_jobs} on glassdoor")
