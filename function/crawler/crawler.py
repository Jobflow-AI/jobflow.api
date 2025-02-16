import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from function.crawler.job_portals import (
    scrape_glassdoor,   # working
    scrape_linkedin,    # working
    scrape_simplyhired, # working
    scrape_indeed,    # working
    scrape_ycombinator,  # working
    scrape_internshala, # working
    scrape_upwork,  # working
    scrape_freelancer, # working
    scrape_foundit,     # Proxy issue
    scrape_naukri   # working, but in non-headless mode
)
import os
import urllib.parse

load_dotenv()

scraperapi_key = os.getenv('SCRAPER_API')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}


searchKeyword = 'web developer'
searchKeyword = urllib.parse.quote(searchKeyword)  # Encodes spaces as %20



jobPortals = {
    "glassdoor": f"https://www.glassdoor.co.in/Job/india-{searchKeyword}-jobs-SRCH_IL.0,5_IN115_KO6,27.htm?sc.keyword={searchKeyword}&sortBy=date_desc",
    # "linkedin": f"https://www.linkedin.com/jobs/search?keywords={searchKeyword}",
    # "simplyhired": f"https://www.simplyhired.co.in/search?q={searchKeyword}",
    # "indeed": f"https://in.indeed.com/jobs?q={searchKeyword}",
    # "ycombinator": f"https://www.workatastartup.com/companies?query={searchKeyword}&sortBy=keyword",
    # "internshala": f"https://internshala.com/jobs/{searchKeyword}-jobs/",
    # "upwork": f"https://www.upwork.com/nx/search/jobs/?q={searchKeyword}",
    # "freelancer": f"https://www.freelancer.com/search/projects?q={searchKeyword}",
    # "naukri": f"https://www.naukri.com/{searchKeyword}-jobs?k={searchKeyword}",
    # "foundit": f"https://www.foundit.in/srp/results?query={searchKeyword}",
}
    

async def scrapejobsdata():
    for portal, url in jobPortals.items():
        print(f"Scraping {portal}: {url}")

        try:
            if portal == 'ycombinator' or portal == 'linkedin':
                response = requests.get(url, headers=headers)
            else:
                proxy_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={url}"
                response = requests.get(proxy_url, headers=headers)

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            with open(f"{portal}.html", "w", encoding="utf-8") as file:
                file.write(soup.prettify())

            if portal == 'linkedin':
                print(portal)
                await scrape_linkedin(soup)

            elif portal == 'glassdoor':
                await scrape_glassdoor(soup)

            elif portal == 'indeed':
                await scrape_indeed(soup)

            elif portal == 'ycombinator':
                await scrape_ycombinator(soup)

            elif portal == 'internshala':
                await scrape_internshala(soup)

            elif portal == 'simplyhired':
                await scrape_simplyhired(soup)

            elif portal == 'foundit':
                await scrape_foundit(soup)

            elif portal == 'upwork':
                await scrape_upwork(soup)

            elif portal == 'freelancer':
                await scrape_freelancer(soup)

            elif portal == 'naukri':
                await scrape_naukri(url)

        except requests.exceptions.RequestException as e:
            print(f"Failed to scrape {portal}: {e}")

