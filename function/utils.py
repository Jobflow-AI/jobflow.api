import requests
from bs4 import BeautifulSoup
import os
import re

scraperapi_key = os.getenv('SCRAPER_API')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def createFile(file, title, company_name, job_link, job_location, job_description = None, skills_required=None, experience_level=None, job_salary=None, source=None, job_type=None):
    # print("inside create file")

    if not company_name and source not in ['upwork', 'freelancer']:
        print("Company name not found. Skipping this job.")
        return

    if title and job_link and job_location:
        # print(title, company_name, "scraping....")
        file.write(f"Job Title: {title}\n")
        if source != 'upwork':
            file.write(f"Company Name: {company_name}\n")
        file.write(f"Job Link: {job_link}\n")
        file.write(f"Job Location: {job_location}\n")
        if job_type or job_location == 'Remote':
            job_type = job_type if job_type else 'Remote'
            file.write(f"Job Type: {job_type}\n")
        if skills_required:
            file.write(f"Skills Required: {', '.join(skills_required)}\n")
        if experience_level:
            file.write(f"Experience Level: {experience_level}\n")
        if job_salary:
            file.write(f"Job Salary: {job_salary}\n")
        if job_description:
            file.write(f"Job Description: {job_description}\n")
        if source:
            file.write(f"Source: {source}\n")
        file.write("\n")
    else:
        print("Missing required fields (title, job_link, or job_location). Skipping this job.")


def fetch_job_details(job_url):
    try:
        response = requests.get(job_url, headers=headers)
        response.raise_for_status()
        job_page = BeautifulSoup(response.text, 'html.parser')

        with open("QJobpage_linkedin.html", "w", encoding="utf-8") as file:
            file.write(job_page.prettify())

        salary_element = job_page.find('div', class_='salary compensation__salary')
        salary = None
        if salary_element:
            salary = salary_element.text.strip()
                
        job_info = {}

        for item in job_page.find_all("li", class_="description__job-criteria-item"):
            criterion = item.find("h3", class_="description__job-criteria-subheader").text.strip() 
            value = item.find("span", class_="description__job-criteria-text").text.strip()
            if value == 'Not Applicable':
                value = None
            job_info[criterion] = value

        return salary, job_info['Seniority level'], job_info['Employment type']

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch salary from {job_url}: {e}")
        return None
    

async def scrape_job_link(job_link, portal):
    try:
        if job_link:
            if portal == 'linkedin':
                response = requests.get(job_link, headers=headers)
            else:
                proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={job_link}"
                response = requests.get(proxy_url, headers=headers)

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            with open(f"Job_{portal}.html", "w", encoding="utf-8") as file:
                file.write(soup.prettify())

            return soup
    
    except requests.exceptions.RequestException as e:
        print(f"Failed to scrape {job_link}: {e}")
        return None

def extract_salary(job_salary):
    if not job_salary:
        return None, None

    job_salary = re.sub(r'\(.*?\)', '', job_salary).strip()

    salary_values = re.findall(r'[\d,]+(?:\.\d+)?', job_salary)

    # Determine salary_min and salary_max
    if len(salary_values) == 2:  
        salary_min, salary_max = salary_values
    elif len(salary_values) == 1:  
        salary_min = salary_max = salary_values[0]
    else:
        salary_min = salary_max = None

    return salary_min, salary_max