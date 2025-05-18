import asyncio
from function.crawler.crawler import scrapejobsdata, scrape_workday_jobs, scrape_linkedin_jobs, scrape_glassdoor_jobs

searchKeywords = [
    "software developer",
    # "data scientist",
    # "full stack developer",
    # "python developer",
    # "project manager",
    # "machine learning engineer",
    # "data analyst",
    # "cloud engineer",
    # "frontend developer",
    # "backend developer",
    # "product manager",
    # "devops engineer",
    # "HR manager",
    # "digital marketing",
    # "business analyst",
    # "sales manager",
    # "AI research scientist",
    # "web developer",
    # "graphic designer",
    # "react developer"
]

async def run_crawler():
    # await scrape_workday_jobs()     
    # Once/Twice Daily
    # 20 jobs, 70 Sec => 
    # Todo :- Add more workday links.

    # LinkedIn
    # await scrape_linkedin_jobs()    
    # Hourly
    # Todo :- Gemini RPM Issue.

    # await scrape_glassdoor_jobs()   
    # Daily
    # Todo :- Check & Scrape properly.
    # - Add all Necessary Keywords
    
    # for keyword in searchKeywords:
    #     await scrapejobsdata(keyword)
    pass

if __name__ == "__main__":
    asyncio.run(run_crawler())
