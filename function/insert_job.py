from datetime import datetime
from db.prisma import db
from flask import jsonify
from prisma.errors import UniqueViolationError

async def insert_job(job):
    # Ensure database connection
    if not db.is_connected():
        await db.connect()

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

        # 🔹 Create job document
        job_document = {
            "title": to_lowercase(job.get('title', 'N/A')),
            "job_link": job.get('job_link', 'N/A'),
            "job_type": to_lowercase(job.get('job_type', 'N/A')),
            "apply_link": job.get('apply_link'),
            "job_location": to_lowercase(job.get('job_location', 'N/A')),
            "salary_min": job.get('salary_min'),
            "salary_max": job.get('salary_max'),
            "job_salary": job.get('job_salary'),  
            "experience_min": job.get('experience_min'),
            "experience_max": job.get('experience_max'),
            "experience": job.get('experience'),
            "job_description": job.get('job_description'),
            "skills_required": ", ".join(job.get('skills_required', [])) if isinstance(job.get('skills_required'), list) else job.get('skills_required', 'N/A'),
            "source": to_lowercase(job.get('source', 'N/A')),
            "source_logo": job.get('source_logo'),
            "posted": job.get('posted', datetime.utcnow()),
            "created_at": datetime.utcnow(),
            "companyId": company.id  # ✅ Ensure this is assigned correctly
        }
        # print(job_document,"\n\n")

        # Check if the job already exists
        existing_job = await db.job.find_first(where={
            "title": job_document['title'],
            "companyId": job_document['companyId']
        })
        if existing_job:
            return jsonify({"error": "Job already exists for this company"}), 400  # Return error or handle differently

        # Proceed to insert the job if it doesn't exist
        job = await db.job.create(data=job_document)
        print(job_document['title']," is added to database\n\n")
        return job

    except Exception as e:
        print(e, "Error from insert_job function")  # Output the error to the console for debugging
        return {'error': str(e)}, 500
    
    finally:
        await db.disconnect()
