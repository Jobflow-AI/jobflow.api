from function.utils import createFile
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

    job_cards = soup.find_all("div", class_="srp-jobtuple-wrapper")
    print(f"✅ Found {len(job_cards)} job listings.")

    job_list = []
    if job_cards:
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in job_cards:
                title = job.find("a", class_="title").text.strip()
                company = job.find("a", class_="comp-name").text.strip()
                location = job.find("span", class_="locWdth").text.strip() if job.find("span", class_="locWdth") else None
                experience = job.find("span", class_="expwdth").text.strip() if job.find("span", class_="expwdth") else None
                salary = job.find("span", class_="sal-wrap").text.strip() if job.find("span", class_="sal-wrap") else None
                job_link = job.find("a", class_="title")["href"]
                job_description = job.find("span", class_="job-desc").text.strip()

                skills = [skill.text.strip() for skill in job.find_all("li", class_="dot-gt tag-li")]

                job_info = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "experience": experience,
                    "salary": salary,
                    "skills": skills,
                    "job_link": job_link,
                    "job_description": job_description,
                    "source": portal
                }

                await insert_job(job_info)
                createFile(file, title, company, job_link, location,job_description, skills, experience, salary, source=portal)