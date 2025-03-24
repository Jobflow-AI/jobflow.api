from function.utils import createFile, fetch_job_details_linkedin, extract_salary
from function.insert_job import insert_job
from function.utils import extract_salary

async def scrape_glassdoor(soup):
    portal = 'glassdoor'
    print("inside glassdoor scrape")
    job_list = soup.find('ul', class_='JobsList_jobsList__lqjTr')
    if job_list:
        jobs = job_list.find_all('li')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title_element = job.find('a', class_='JobCard_jobTitle__GLyJ1')
                title = title_element.text.strip() if title_element else None
                company_name_element = job.find('span', class_='EmployerProfile_compactEmployerName__9MGcV')
                company_name = company_name_element.text.strip() if company_name_element else None
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

                job_description_section = job.find('div', class_='JobCard_jobDescriptionSnippet__l1tnl')
                job_description = None
                skills = []
                if job_description_section:
                    description_divs = job_description_section.find_all('div')
                    if len(description_divs) > 0:
                        job_description = description_divs[0].text.strip()
                    if len(description_divs) > 1:
                        skills_section = description_divs[1]
                        if skills_section:
                            skills_text = skills_section.text.strip().replace('Skills:', '').strip()
                            skills = [skill.strip() for skill in skills_text.split(',')]
                
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
                        "experience_level": None,
                        "job_description": job_description,
                        "source": portal
                    }
                    try:
                        await insert_job(job_info)
                        createFile(file, title, company_name, job_link, job_location, job_description, skills, None, job_salary, portal, None)
                    except Exception as e:
                        print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
