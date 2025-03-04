import asyncio
from function.crawler.crawler import scrapejobsdata

searchKeywords = [
    "software developer",
    "data scientist",
    "full stack developer",
    "python developer",
    "project manager",
    "machine learning engineer",
    "data analyst",
    "cloud engineer",
    "frontend developer",
    "backend developer",
    "product manager",
    "devops engineer",
    "HR manager",
    "digital marketing",
    "business analyst",
    "sales manager",
    "AI research scientist",
    "web developer",
    "graphic designer",
    "react developer"
]

async def run_crawler():
    for keyword in searchKeywords:
        await scrapejobsdata(keyword)

if __name__ == "__main__":
    asyncio.run(run_crawler())
