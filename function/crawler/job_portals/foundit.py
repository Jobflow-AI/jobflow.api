from function.utils import createFile, fetch_job_details
from function.insert_job import insert_job

async def scrape_foundit(soup):
    portal = 'foundit'

    job_cards = soup.find_all("div", class_="cardContainer")
    print(f"✅ Found {len(job_cards)} job listings.")

    job_list = []
    if job_cards:
        with open(f"{portal}_jobs.txt", "w", encoding="utf-8") as file:
            for job in job_cards:
                title = job.find("div", id="jobCardTitle").text.strip()
                company = job.find("div", class_="companyName").text.strip()
                location = job.find("div", class_="details location").text.strip() if job.find("div", class_="details location") else None
                experience = job.find("div", class_="experienceSalary").text.strip() if job.find("div", class_="experienceSalary") else None
                posted_time = job.find("p", class_="timeText").text.strip() if job.find("p", class_="timeText") else None

                job_id = job.get("id")
                job_link = f"https://www.foundit.in/job/{job_id}" if job_id else None

                job_info = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "experience": experience,
                    "posted_time": posted_time,
                    "job_link": job_link,
                    "source": portal
                }

                await insert_job(job_info)
                createFile(file, title, company, job_link, location, None, None, experience, None, portal, None)
