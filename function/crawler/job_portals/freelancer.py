
from function.utils import createFile, fetch_job_details
from function.insert_job import insert_job
async def scrape_freelancer(soup):
    portal = 'freelancer'
    job_list = soup.find('div', id='project-list')
    if job_list:
        jobs = job_list.find_all('div', class_="JobSearchCard-item")

        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title_element = job.find('a', class_='JobSearchCard-primary-heading-link')
                title = title_element.text.strip() if title_element else "No title"
                job_link = title_element['href'] if title_element else "No link"
                job_description_element = job.find('p', class_='JobSearchCard-primary-description')
                job_description = job_description_element.text.strip() if job_description_element else None
                job_location = "Remote"
                job_salary_element = job.find('div', class_='JobSearchCard-primary-price')
                job_salary = job_salary_element.find(text=True, recursive=False).strip() if job_salary_element else None

                skills_section = job.find('div', class_='JobSearchCard-primary-tags')
                skills_required = []
                if skills_section:
                    skills = skills_section.find_all('a', class_='JobSearchCard-primary-tagsLink')
                    skills_required = [skill.text.strip() for skill in skills if skill.text.strip()]


                job_info = {
                    "title": title,
                    "job_link": f"https://www.freelancer.com{job_link}",
                    "job_location": job_location,
                    "job_salary": job_salary,
                    "job_description": job_description,
                    "skills_required": skills_required,
                    "source": portal
                }
                await insert_job(job_info)

                # print(title, job_link, job_location)
                createFile(file, title, None, f"https://www.freelancer.com{job_link}", job_location, job_description, skills_required, None, job_salary, portal)
