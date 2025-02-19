from function.utils import createFile, extract_salary
from function.insert_job import insert_job

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

async def scrape_naukri(base_url):
    portal = 'naukri'

    options = Options()
    # options.add_argument("--headless=new")  
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080") 
    options.add_argument("--no-sandbox")  
    options.add_argument("--disable-dev-shm-usage")

    # Initialize WebDriver with options
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get(base_url)
    time.sleep(5)

    # ✅ BeautifulSoup parsing
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    job_list = soup.find_all("div", class_="srp-jobtuple-wrapper")
    print(f"✅ Found {len(job_list)} job listings.")

    if job_list:
        job_cards = job_list
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in job_cards:
                title_tag = job.find("a", class_="title")
                title = title_tag.text.strip() if title_tag else None


                company_tag = job.find("a", class_="comp-name")
                company = company_tag.text.strip() if company_tag else None
                company_logo_tag = job.find("img", class_="logoImage")
                company_logo = company_logo_tag["src"] if company_logo_tag else None

                location_tag = job.find("span", class_="locWdth")
                location = location_tag.text.strip() if location_tag else None

                experience_tag = job.find("span", class_="expwdth")
                experience = experience_tag.text.strip() if experience_tag else None

                salary_tag = job.find("span", class_="sal-wrap")
                job_salary = salary_tag.text.strip() if salary_tag else None

                job_link = title_tag["href"] if title_tag and "href" in title_tag.attrs else None

                job_description_tag = job.find("span", class_="job-desc")
                job_description = job_description_tag.text.strip() if job_description_tag else None

                skills = [skill.text.strip() for skill in job.find_all("li", class_="dot-gt tag-li")]

                salary_max = None
                salary_min = None
                if job_salary:
                    salary_min, salary_max = extract_salary(job_salary)  

                job_info = {
                    "title": title,
                    "company_name": company,
                    "company_logo": company_logo,
                    "job_location": location,
                    "experience": experience,
                    "job_salary": job_salary,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "skills_required": skills,
                    "job_link": job_link,
                    "job_description": job_description,
                    "source": portal,
                }

                await insert_job(job_info)
                createFile(file, title, company, job_link, location, job_description, skills, experience, job_salary, source=portal)