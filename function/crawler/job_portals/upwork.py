
from function.utils import createFile, fetch_job_details, extract_salary
from function.insert_job import insert_job
from function.utils import extract_salary

async def scrape_upwork(soup):
    portal = 'upwork'
    job_list = soup.find('section', attrs={'data-ev-label': 'search_result_impression'})
    if job_list:
        jobs = job_list.find_all('article')

        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title_element = job.find('h2', class_='job-tile-title').find('a')
                title = title_element.text.strip() if title_element else "No title"
                job_link = title_element['href'] if title_element else "No link"
                job_location = "Remote"

                # Extract job type, experience level, and budget
                job_info_list = job.find('ul', class_='job-tile-info-list')
                experience_level = None
                job_salary = None
                salary_min = None
                salary_max = None

                if job_info_list:
                    for item in job_info_list.find_all('li'):
                        data_test = item.get('data-test')
                        if data_test == "experience-level":
                            experience_level = item.find('strong').text.strip()
                        elif data_test == "is-fixed-price":
                            budget_strong_tags = item.find_all('strong')
                            if len(budget_strong_tags) > 1:
                                job_salary = budget_strong_tags[1].text.strip()  

                if job_salary:
                    salary_min, salary_max = extract_salary(job_salary)  

                # Extract Skills Required
                skills_section = job.find('div', class_='air3-token-container')
                skills_required = []
                if skills_section:
                    skills = skills_section.find_all('button', class_='air3-token')
                    skills_required = [skill.find('span').text.strip() for skill in skills if skill.find('span')]

                job_info = {
                    "title": title,
                    "job_link": f"https://www.upwork.com{job_link}",
                    "company_name": "Upwork",
                    "job_location": job_location,
                    "job_salary": job_salary,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "skills_required": skills_required,
                    "experience_level": experience_level,
                    "source": portal
                }
                await insert_job(job_info)
                createFile(file, title, None, f"https://www.upwork.com{job_link}", job_location, None, skills_required, experience_level, job_salary, portal,"Remote")