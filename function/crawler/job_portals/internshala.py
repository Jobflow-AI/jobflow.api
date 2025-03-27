
from function.utils import createFile, fetch_job_details_linkedin
from function.insert_job import insert_job
async def scrape_internshala(soup):
    portal = 'internshala'
    job_list = soup.find('div', id='list_container')
    if job_list:
        jobs = job_list.find_all('div', class_='internship_meta')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title = job.find('h3', class_='job-internship-name')
                company_name = job.find('p', class_='company-name')
                job_link = job.find_parent('div', class_='individual_internship')[
                    'data-href'] if job.find_parent('div', class_='individual_internship') else None
                job_location = job.find('div', class_='individual_internship_details').find('a')

                createFile(file, title.text.strip(), company_name.text.strip(), job_link, job_location.text.strip())

                if title and company_name and job_link and job_location:
                    job_info = {
                        "title": title.text.strip(),
                        "company_name": company_name.text.strip(),
                        "job_link": f"https://internshala.com{job_link}",
                        "job_location": job_location.text.strip(),
                        "job_salary": None,
                        "source": portal
                    }
                    await insert_job(job_info)