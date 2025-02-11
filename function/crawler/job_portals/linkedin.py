from function.utils import createFile, fetch_job_details
from function.insert_job import insert_job
async def scrape_linkedin(soup):
     portal = 'linkedin'
     job_list = soup.find('ul', class_='jobs-search__results-list')
     if job_list:
        jobs = job_list.find_all('li')
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in jobs:
                title = job.find('h3', class_='base-search-card__title')
                company_name = job.find('h4', class_='base-search-card__subtitle')
                job_link = job.find('a', class_='base-card__full-link')
                job_location = job.find('span', class_='job-search-card__location')
                job_salary, experience_level, job_type = fetch_job_details(job_link['href'].strip()) if job_link else None
                company_logo_element = job.find('div', class_='search-entity-media')
                company_logo=None
                if company_logo_element:
                    img_tag= company_logo_element.find('img')
                    if img_tag: 
                        company_logo = img_tag['data-delayed-url']

                if title and company_name and job_link and job_location:
                    job_info = {
                        "title": title.text.strip(),
                        "company_name": company_name.text.strip(),
                        "company_logo": company_logo,
                        "job_link": job_link['href'].strip(),
                        "job_location": job_location.text.strip(),
                        "job_salary": job_salary,
                        "experience_level": experience_level,
                        "job_type": job_type,
                        "source": portal,
                    }
                    try:
                        await insert_job(job_info)
                        createFile(file, title.text.strip(), company_name.text.strip(), job_link['href'].strip(), job_location.text.strip(), None, None, experience_level, job_salary, portal, job_type)
                    except Exception as e:
                        print(f"Error inserting job for {job_info.get('title', 'unknown')}: {e}")
                    

async def scrape_linkedin_jobpage(soup, job_link):
    portal = 'linkedin'
    
    if not soup:
        return None
    
    # Initialize job data dictionary with default values
    job_info = {
        "title": None,
        "job_link": job_link,
        "job_location": None,
        "company_name": None,
        "company_logo": None,
        "source": portal
    }
    
    try:
        # Extract job title
        title_element = soup.find('h3', class_="sub-nav-cta__header")
        if title_element:
            job_info["title"] = title_element.text.strip()
        
        # Extract company details and location
        job_title_element = soup.find('div', class_='sub-nav-cta__text-container')
        if job_title_element:
            company_element = job_title_element.find('a', class_="sub-nav-cta__optional-url")
            location_element = job_title_element.find('span')
            
            if company_element:
                job_info["company_name"] = company_element.text.strip()
            if location_element:
                job_info["job_location"] = location_element.text.strip()
        
        # Extract company logo
        company_logo_element = soup.find('div', class_='sub-nav-cta__content')
        if company_logo_element and (img_tag := company_logo_element.find('img')):
            job_info["company_logo"] = img_tag.get('data-delayed-url')
        
        # Validate required fields
        if not all([job_info["title"], job_info["company_name"]]):
            print(f"Warning: Missing required fields for job listing: {job_link}")
            
        return job_info
        
    except Exception as e:
        print(f"Error scraping LinkedIn job page: {str(e)}")
        return None