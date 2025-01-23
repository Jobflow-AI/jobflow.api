from db.prisma import db
from flask import g, jsonify

async def checkExistingJob(jobdata):
    try:
        await db.connect()

        print(jobdata, "here is the job data")

        title = jobdata['title'].lower()
        company_name = jobdata['company_name'].lower()
        print(title, g.user.id, company_name, "here is the deteial id")

        # Find tracked job for this user where the related job has matching title
        existing_job = await db.tracked_jobs.find_first(
            where={
                'userId': g.user.id,
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

        # if (
        #     existing_job
        #     and existing_job.company
        #     and existing_job.company.company_name != company_name
        # ):
        #     print({"success": False, "message": "Company name does not match"}), 400
        #     return jobdata          

        # If job doesn't exist, return None
        if not existing_job:
            return jobdata
        
        # Get company details safely
        company = existing_job.company if existing_job else None
        
        formatted_job = {
            "userId": g.user.id,
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
    finally:
        await db.disconnect()