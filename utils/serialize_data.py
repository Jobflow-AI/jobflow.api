def serialize_job(job):
    return {
        'id': job.id,
        'title': job.title,
        'company': {
            'name': job.company.company_name,
            'logo': job.company.company_logo,
            'description': job.company.description
        },
        'job_location': job.job_location,
        'job_type': job.job_type,
        'job_salary': job.job_salary,
        'job_link': job.job_link,
        'source': job.source
    }
