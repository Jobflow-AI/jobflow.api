from function.utils import createFile, scrape_job_link
from function.insert_job import insert_job

async def scrape_ycombinator(soup):
    portal = 'ycombinator'
    # Locate all job entries
    jobs = soup.find_all('div', class_='w-full bg-beige-lighter mb-2 rounded-md p-2 border border-gray-200 flex')

    if jobs:
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                # Extract job title
                title_tag = job.find('div', class_='job-name').find('a')
                title = title_tag.text.strip() if title_tag else None

                # Extract job link
                job_link = title_tag['href'] if title_tag and 'href' in title_tag.attrs else None

                # Extract job location
                job_details = job.find('p', class_='job-details')
                if job_details:
                    spans = job_details.find_all('span')
                    if len(spans) > 1:  # Ensure there are at least two spans
                        job_location = spans[1].text.strip()  # Extract text from the second span
                    else:
                        job_location = "Not specified"  # Fallback if the second span doesn't exist
                else:
                    job_location = "Not specified"
                
                company_name = job.find('div', class_='company-details').find('span')
                company_logo_element = job.find('div', class_='company-logo')
                company_logo = None
                if company_logo_element:
                    img_tag = company_logo_element.find('img')
                    if img_tag:
                        company_logo = img_tag['src']

                job_details = await scrape_job_link(job_link, portal)
                job_salary=None
                if job_details:
                    job_salary_element = job_details.find('div', class_="company-title")
                    if job_salary_element:
                        job_salary = job_salary_element.find('div', class_='text-gray-500 my-2').find('span').text.strip()

                salary_min = None
                salary_max = None

                if job_salary:
                    salary_min, salary_max = extract_salary(job_salary)  

                # Construct job info dictionary
                job_info = {
                    "title": title,
                    "job_link": job_link,
                    "job_location": job_location,
                    "company_name": company_name.text.strip() if company_name else None,
                    "company_logo": company_logo,
                    "job_salary": job_salary,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "source": portal
                }

                # Insert the job info into the database
                await insert_job(job_info)
                createFile(file, title, company_name.text.strip() if company_name else None, job_link, job_location, None, None, job_salary, source=portal)

async def scrape_ycombinator_jobpage(soup, job_link):
    portal = 'ycombinator'
    print(portal, "here inside job")
    if soup:
        job_title = soup.find('span', class_="company-name")
        if job_title:
            # Extract both job title and company name
            title_text = job_title.text.strip()
            if "at" in title_text:
                parts = title_text.split("at")
                job_title_name = "at".join(parts[:-1]).strip()  # Join all parts before the last "at"
                company_name = parts[-1].strip()  # Get the part after last "at"
            else:
                job_title_name = title_text
                company_name = None  # Handle case where "at" is not found

        job_title_element = soup.find('div', class_='company-title').find_all('div', class_='text-gray-500')
        if job_title_element:
            job_salary_text = job_title_element[0].find('span').text.strip()  # Extracting the first div for location
            job_location_text = job_title_element[2].text.strip()  # Extracting the third div for location
            job_type_text = job_title_element[3].text.strip()  # Extracting the fourth div for job type
        else:
            job_location_text = None
            job_type_text = None

        company_logo_element = soup.find('div', class_='company-logo')
        company_logo = None
        if company_logo_element:
            img_tag = company_logo_element.find('img')
            if img_tag:
                company_logo = img_tag['src']

        job_info = {
            "title": job_title_name,  # Use the extracted job title
            "job_link": job_link,
            "job_location": job_location_text,  # Use the extracted job location
            "job_type": job_type_text,  # New field for job type
            "company_name": company_name,  # Use the extracted company name
            "company_logo": company_logo,
            "job_salary": job_salary_text,
            "source": portal
        }

        # print(job_info, "end of funciotns")

        return job_info
