from db.prisma import db
from fastapi import Depends
from typing import Optional
from .middleware import get_current_user

async def checkExistingJob(jobdata, current_user = Depends(get_current_user)):
    try:
        title = jobdata['title'].lower()
        company_name = jobdata['company_name'].lower()
        print(title, current_user.id, company_name, "here is the detail id")

        # Find tracked job for this user where the related job has matching title
        existing_job = await db.tracked_jobs.find_first(
            where={
                'userId': current_user.id,
                'title': title,
                'company': {  # Add a nested condition for the related company
                    'company_name': company_name
                }
            },
            include={
                'company': True  # Include the company details for use later
            }
        )

        print(existing_job, "here is the existing job")

        # If job doesn't exist, return None
        if not existing_job:
            return jobdata
        
        # Get company details safely
        company = existing_job.company if existing_job else None
        
        formatted_job = {
            "userId": current_user.id,
            "title": existing_job.title.upper(),
            "status": existing_job.status,
            "company_name": company.company_name if company else None,
            "company_logo": company.company_logo if company else None,
            "job_link": existing_job.job_link,
            "job_type": existing_job.job_type,
            "job_location": existing_job.job_location,
            "job_salary": existing_job.job_salary,
            "source": existing_job.source
        }
        
        return formatted_job
            
    except Exception as e:
        print(e, "Error in checkExistingJob function")
        return jobdata