import asyncio
from function.crawler.crawler import scrapejobsdata, scrape_workday_jobs, scrape_linkedin_jobs

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
    await scrape_workday_jobs()
    await scrape_linkedin_jobs()
    # for keyword in searchKeywords:
    #     await scrapejobsdata(keyword)

if __name__ == "__main__":
    asyncio.run(run_crawler())
