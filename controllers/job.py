from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from db.prisma import db
from middleware import get_current_user
from function.crawler.crawler import scrapejobsdata
from function.crawler.run_crawler import run_crawler
from utils import serialize_job
import os
from function.utils import scrape_job_link
from function.crawler.job_portals import scrape_ycombinator_jobpage, scrape_linkedin_jobpage
from function.job_expires.job_expirations import run_job_expiration
from utils.functions import checkExistingJob
from datetime import datetime, timedelta

# Router
job_router = APIRouter()

@job_router.get('/')
async def create_jobs():
    try:
        await run_crawler()
        return "Successfully inserted job"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@job_router.get('/get')
async def get_job(
    page: int = Query(1, ge=1),
    portal: Optional[str] = None,
    title: Optional[str] = None
):
    try:
        page_size = 10
        skip = (page - 1) * page_size

        filter_conditions = {}
        if portal: 
            filter_conditions['source'] = portal
        if title:
            filter_conditions['title'] = {"contains": title}

        # Fetch jobs from the database including the company relation
        jobs = await db.job.find_many(
            where=filter_conditions,
            skip=skip,
            take=page_size,
            include={'company': True}
        )

        # Serialize the job data
        serialized_jobs = [job.model_dump() for job in jobs]

        return {'jobs': serialized_jobs, 'page': page, 'page_size': page_size}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@job_router.get('/get/id')
async def getJobId():   
    try:
        # if not db.is_connected():
        #     await db.connect()

        jobId = request.args.get('jobId', default=1, type=int)

        # Fetch jobs from the database including the company relation
        job = await db.job.find_unique(
            where={"id": jobId},
        )

        # Serialize the job data
        serialized_job = serialize_job(job) 

        return jsonify({'job': serialized_job }), 200

    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    
    # finally:
    #     # Disconnect Prisma client
    #     await db.disconnect()

@job_router.get('/get/company/list')
async def get_companies_list():   
    try:
        # Remove the db connection check and connect call

        # Fetch jobs from the database including the company relation
        companies = await db.company.find_many()

        serialized_companies = [company.model_dump() for company in companies]
        return jsonify({'companies': serialized_companies}), 200

    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    
    # Remove the finally block with db.disconnect()


@job_router.get('/scrape')
async def scrape_job():   
    try:
        portal = request.args.get("portal", default='', type=str) 
        job_link = request.args.get("job_link", default='', type=str)

        print(job_link, portal, "here is info") 

        soup = await scrape_job_link(job_link, portal)
        jobdata = {}

        if portal == 'ycombinator':
            print(portal)
            jobdata = await scrape_ycombinator_jobpage(soup, job_link)

        # elif portal == 'glassdoor':
        #     print(portal)
        #     # jobdata = await scrape_glassdoor(soup)

        # elif portal == 'indeed':
        #     print(portal)
        #     # jobdata = await scrape_indeed(soup)

        elif portal == 'linkedin':
            print(portal)
            jobdata = await scrape_linkedin_jobpage(soup, job_link)

        # # elif portal == 'internshala':
        # #     await scrape_internshala(soup)

        # elif portal == 'simplyhired':
        #     print(portal)
        #     await scrape_simplyhired(soup)

        # elif portal == 'upwork':
        #     await scrape_upwork(soup)

        # elif portal == 'freelancer':
        #     await scrape_freelancer(soup) 

        # print(jobdata)
        jobdata = await checkExistingJob(jobdata)
        
        return jobdata

    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500

@job_router.get('/expire')
# @protect_route()
async def expire_jobs():   
    try:
        # Remove the db connection check and connect call
            
        print("Running scheduled job expiration")
        # Run the job expiration process
        expired_count = await run_job_expiration()
        
        return jsonify({
            'success': True,
            'message': f'Successfully expired {expired_count} jobs',
            'expired_count': expired_count
        }), 200
    
    except Exception as e:
        print(f"Error in expire_jobs function: {e}")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    
    # Remove the finally block with db.disconnect()

@job_router.get('/stats')
async def get_job_stats():   
    try:
        # Remove the db connection check and connect call
            
        # Get total jobs
        total_jobs = await db.job.count()
        
        # Get active jobs
        active_jobs = await db.job.count(
            where={
                "status": "active"
            }
        )
        
        # Get jobs with end_date in the past
        current_date = datetime.now()
        expired_end_date = await db.job.count(
            where={
                "end_date": {"lte": current_date},
                "status": "active"
            }
        )
        
        # Get jobs older than 30 days
        thirty_days_ago = current_date - timedelta(days=30)
        old_jobs = await db.job.count(
            where={
                "posted": {"lte": thirty_days_ago},
                "status": "active"
            }
        )
        
        return jsonify({
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'jobs_with_expired_end_date': expired_end_date,
            'jobs_older_than_30_days': old_jobs,
            'current_time': current_date.isoformat(),
            'thirty_days_ago': thirty_days_ago.isoformat()
        }), 200
    
    except Exception as e:
        print(f"Error in get_job_stats: {e}")
        return jsonify({'error': str(e)}), 500
    
    # Remove the finally block with db.disconnect()