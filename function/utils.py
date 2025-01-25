import requests
from bs4 import BeautifulSoup
import os

scraperapi_key = os.getenv('SCRAPER_API')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def createFile(file, title, company_name, job_link, job_location, job_salary=None, source=None):
    print("inside create file")
    if title and company_name and job_link and job_location:
        print(title, company_name, "scrapiing....")
        file.write(f"Job Title: {title}\n")
        file.write(f"Company Name: {company_name}\n")
        file.write(f"Job Link: {job_link}\n")
        file.write(f"Job Location: {job_location}\n")
        if job_salary:
            file.write(f"Job Salary: {job_salary}\n")
        if source:
            file.write(f"Source: {source}\n")
        file.write("\n")

def fetch_job_salary(job_url):
    try:
        response = requests.get(job_url, headers=headers)
        response.raise_for_status()
        job_page = BeautifulSoup(response.text, 'html.parser')

        with open("QJobpage_linkedin.html", "w", encoding="utf-8") as file:
            file.write(job_page.prettify())

        salary_element = job_page.find('div', class_='salary compensation__salary')
        if salary_element:
            return salary_element.text.strip()
        else:
            return None
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
