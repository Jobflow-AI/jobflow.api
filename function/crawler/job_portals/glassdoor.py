
from function.utils import createFile, fetch_job_details
from function.insert_job import insert_job
async def scrape_glassdoor(soup):
    portal = 'glassdoor'
    print("inside glasdorr scarpe")
    job_list = soup.find('ul', class_='JobsList_jobsList__lqjTr')
    if job_list:
        jobs = job_list.find_all('li')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title = job.find('a', class_='JobCard_jobTitle__GLyJ1')
                company_name = job.find('span', class_='EmployerProfile_compactEmployerName__9MGcV') 
                job_link = title['href'] if title else None
                job_location = job.find('div', class_='JobCard_location__Ds1fM')
                job_salary = job.find('div', class_='JobCard_salaryEstimate__QpbTW')

                logo_tag = job.find('img', class_='avatar-base_Image__2RcF9')
                logo_url = None
                if logo_tag and 'src' in logo_tag.attrs:
                    logo_url = logo_tag['src']

                company_logo = logo_url

                job_description_section = job.find('div', class_='JobCard_jobDescriptionSnippet__l1tnl')
                job_description = None
                if job_description_section:
                    job_description = job_description_section.find_all('div')[0].text.strip()
                
                skills = []
                if job_description_section:
                    skills_section = job_description_section.find_all('div')[1]
                    if skills_section:
                        skills_text = skills_section.text.strip().replace('Skills:', '').strip()
                        skills = [skill.strip() for skill in skills_text.split(',')]
                
 
                if title and company_name and job_link and job_location:
                    job_info = {
                        "title": title.text.strip(),
                        "company_name": company_name.text.strip(),
                        "company_logo": company_logo,
                        "job_link": job_link,
                        "job_location": job_location.text.strip(),
                        "job_salary": job_salary.text.strip() if job_salary else None,
                        "skills_required": skills,
                        "experience_level": None,
                        "job_description": job_description,
                        "source": portal
                    }
                    try:
                        await insert_job(job_info)
                        createFile(file, title.text.strip(), company_name.text.strip(), job_link, job_location.text.strip(), job_description, skills, None, job_salary.text.strip() if job_salary else None, portal, None)
                    except Exception as e:
                        print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
