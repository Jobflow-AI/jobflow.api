from datetime import datetime
from db.prisma import db
from flask import jsonify
from prisma.errors import UniqueViolationError
import hashlib
import logging

logging.basicConfig(filename= 'log.txt',  level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def insert_job(job):
    # Ensure database connection
    # if not db.is_connected():
    #     await db.connect()

    try:
        def to_lowercase(value):
            return value.lower() if isinstance(value, str) else 'n/a'
        
        company_name = job.get('company_name', '').strip().lower()  # Normalize input
        
        if not company_name:
            return jsonify({"error": "Company Name is required"}), 400

        # Check if company already exists in the database
        company = await db.company.find_unique(where={'company_name': company_name})
        if not company:
            try:
                company = await db.company.create(
                    data={
                        "company_name": company_name,
                        "company_logo": job.get('company_logo'),
                        "description": job.get('company_desc')
                    }
                )
            except UniqueViolationError:  # Handle race condition where another insert happened
                company = await db.company.find_unique(where={'company_name': company_name})

        # Ensure company exists
        if not company:
            return jsonify({"error": "Failed to create or find company"}), 500

        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')

        # Remove commas from salary strings
        salary_min = salary_min.replace(',', '') if salary_min is not None else None
        salary_max = salary_max.replace(',', '') if salary_max is not None else None

        # Generate a unique job_id if not provided
        job_id = job.get('job_id', 'N/A')
        if job_id == 'N/A':
            unique_string = f"{job.get('title', '')}-{company_name}-{datetime.utcnow().isoformat()}"
            job_id = hashlib.md5(unique_string.encode()).hexdigest()

        # # Convert to float
        # salary_min = float(salary_min) if salary_min is not None else None
        # salary_max = float(salary_max) if salary_max is not None else None

        posted_str = job.get("posted")
        if posted_str:
            try:
                posted_date = datetime.strptime(posted_str, "%Y-%m-%d")
            except ValueError:
                posted_date = datetime.utcnow()
        else:
            posted_date = datetime.utcnow()

        end_date_str = job.get("end_date")
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                end_date = None
        else:
            end_date = None

        # 🔹 Create job document
        job_document = {
            "title": job.get('title', 'N/A'),
            "job_id": job_id,
            "job_link": job.get('job_link', 'N/A'),
            "job_type": job.get('job_type', 'N/A'),
            # "apply_link": job.get('apply_link'),
            "job_location": job.get('job_location', 'N/A'),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_salary": job.get('job_salary'),  
            "experience_min": job.get('experience_min'),
            "experience_max": job.get('experience_max'),
            "experience": job.get('experience'),
            "job_description": job.get('job_description'),
            "skills_required": ", ".join(job.get('skills_required', [])) if isinstance(job.get('skills_required'), list) else job.get('skills_required', 'N/A'),
            "source": job.get('source', 'N/A'),
            "source_logo": job.get('source_logo'),
            "posted": posted_date,
            "end_date": end_date,
            "companyId": company.id  # ✅ Ensure this is assigned correctly
        }
        # print(job_document,"\n\n")

        # Check if the job already exists
        existing_job = await db.job.find_first(where={
            "title": job_document['title'],
            "companyId": job_document['companyId'],
            "status": "active"
        })
        if existing_job:
            logger.info(f"{job_document['title']} already exists for this company")
            return jsonify({"error": "Job already exists for this company"}), 400  # Return error or handle differently

        # Proceed to insert the job if it doesn't exist
        job = await db.job.create(data=job_document)
        logger.info(f"{job_document['title']} is added to database")
        return job

    except Exception as e:
        logger.error("Error from insert_job function", str(e))  # Output the error to the console for debugging
        return {'error': str(e)}, 500
    # finally:
    #     await db.disconnect()
