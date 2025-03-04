from function.utils import createFile, fetch_job_details, extract_salary
from function.insert_job import insert_job
from function.utils import extract_salary

async def scrape_simplyhired(soup):
    portal = 'simplyhired'

    job_list = soup.find('ul', id='job-list')
    if job_list:
        jobs = job_list.find_all('li')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title_element = job.find('a', class_='chakra-button css-1djbb1k')
                company_name_element = job.find('span', class_='css-lvyu5j').find('span')
                job_link_element = title_element['href']
                job_location_element = job.find('span', class_='css-1t92pv')
                job_salary_element = job.find('p', class_='chakra-text css-1g1y608')


                title = title_element.text.strip() if title_element else "N/A"
                company_name = company_name_element.text.strip() if company_name_element else "N/A"
                job_link = "https://www.simplyhired.co.in" + job_link_element if job_link_element else "N/A"
                job_location = job_location_element.text.strip() if job_location_element else "N/A"
                job_salary = job_salary_element.text.strip() if job_salary_element else "N/A"

                salary_min = None
                salary_max = None

                if job_salary:
                    salary_min, salary_max = extract_salary(job_salary)  

                job_info = {
                    "title": title,
                    "company_name": company_name,
                    "job_link": job_link,
                    "job_location": job_location,
                    "job_salary": job_salary,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "source": portal
                }
                await insert_job(job_info)
                createFile(file, title, company_name, job_link, job_location, None, None, None, job_salary, portal, None)