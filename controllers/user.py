from sqlite3 import connect
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any, Union
from db.prisma import db
from middleware import get_current_user
from utils import serialize_job, extract_text, allowed_file, parse_resume, process_resume_upload
from function.insert_job import insert_job
from datetime import datetime
import json
import tempfile
import os
import fitz
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Define Pydantic models for request/response validation
class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class JobStatusUpdate(BaseModel):
    status: str

class JobTrackRequest(BaseModel):
    jobId: str
    status: str

class CreateJobRequest(BaseModel):
    title: str
    companyId: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    company_description: Optional[str] = None
    job_link: Optional[str] = None
    job_location: Optional[str] = None
    job_type: Optional[str] = None
    job_salary: Optional[str] = None
    job_description: Optional[str] = None
    skills_required: Optional[str] = None
    source: Optional[str] = None
    source_logo: Optional[str] = None
    status: Optional[str] = "applied"

# Create router
user_router = APIRouter()

@user_router.get('/get')
async def get_user(current_user: dict = Depends(get_current_user)):
    try:
        # Include job_statuses and resume sections in the query
        user = await db.user.find_unique(
            where={"id": current_user.id},
            include={
                'job_statuses': True,
                'resume': True  # Include resume data
            }
        )
        if not user:
            print("user not exists")
            raise HTTPException(status_code=400, detail="User does not exist")
        
        user_dict = user.model_dump()
        return {"success": True, "user": user_dict}

except Exception as e:
print(f"Resume upload error: {str(e)}")
raise HTTPException(status_code=500, detail=str(e))
finally:
# Cleanup temporary files
if temp_dir and os.path.exists(temp_dir):
for root, dirs, files in os.walk(temp_dir, topdown=False):
for name in files:
os.remove(os.path.join(root, name))
os.rmdir(root)
    try:
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(status_code=400, detail="User does not exist")

        # Convert Pydantic model to dict and remove None values
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        updated_user = await db.user.update(
            where={"id": current_user.id},
            data=update_dict
        )
        
        return {"success": True, "user": updated_user.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Update error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get('/jobs/get')
async def get_user_jobs(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(status_code=404, detail="User does not exist")

        print(f"Filtering jobs with status: {status}")

        # Build query conditions
        where_condition = {"userId": user.id}
        if status:
            where_condition["status"] = status

        # Fetch user's applied jobs
        userAppliedJobs = await db.tracked_jobs.find_many(
            where=where_condition,
            include={
                'job': {
                    'include': {
                        'company': True
                    }
                }
            }
        )
        
        jobs_serialized = [job.model_dump() for job in userAppliedJobs]
        print(jobs_serialized, "here are the jobs")
        return {"success": True, "jobs": jobs_serialized}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post('/job/track')
async def track_job(
    jobId: str = Query(..., description="Job ID to track"),
    status: str = Query(..., description="Job status"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Validate status against JobStatus enum
        if status.upper() not in ['APPLIED', 'ACCEPTED', 'REJECTED']:
            raise HTTPException(status_code=400, detail="Invalid job status")

        job = await db.job.find_unique(where={"id": jobId})
        if not job:
            raise HTTPException(status_code=404, detail="Job does not exist")

        print(jobId, status, "here are jobid and status")

        # Check existing tracking
        existing_tracking = await db.tracked_jobs.find_first(
            where={
                "userId": current_user.id,
                "jobId": jobId
            }
        )
        
        if existing_tracking:
            raise HTTPException(status_code=400, detail="Job already tracked")

        # Create tracking entry with proper enum value
        await db.tracked_jobs.create(
            data={
                "userId": current_user.id,
                "jobId": jobId,
                "status": status.upper(),
            }
        )

        return {"success": True, "message": "Job tracked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(e, "here is the error")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.put('/job/update/status')
async def update_job_status(
    jobId: str = Query(..., description="Job ID to update"),
    status: str = Query(..., description="New job status"),
    current_user: dict = Depends(get_current_user)
):
    try:
        print(jobId, status, "here are jobid and status")

        applied_job = await db.tracked_jobs.find_unique(
            where={"userId": current_user.id, "id": jobId}
        )
        
        if not applied_job:
            raise HTTPException(status_code=400, detail="Applied Job not exists")
        
        # Update the job status
        await db.tracked_jobs.update(
            where={"userId": current_user.id, "id": jobId},
            data={"status": status}
        )
        
        return {"success": True, "message": "Job status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(e, "here is the error")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post('/job/bookmark')
async def bookmark_job(
    jobId: str = Query(..., description="Job ID to bookmark"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Find the job by its ID
        job = await db.job.find_unique(where={"id": jobId})
        if not job:
            raise HTTPException(status_code=404, detail="Job does not exist")
        
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(status_code=400, detail="User does not exist")
        
        await db.user.update(
            where={"id": current_user.id},
            data={
                "bookmarked_jobs": {
                    "push": jobId  # Use 'push' to add the jobId to the array
                }
            }
        )
        
        return {"success": True, "message": "Job bookmarked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(e, "here is the error")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post('/job/create')
async def create_job(
    job_data: CreateJobRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        print(job_data, "here is the body data")

        # Fetch the current user
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user:
            raise HTTPException(status_code=400, detail="User does not exist")

        # Prepare fields with validation
        title = job_data.title.lower() if job_data.title else None
        company_id = job_data.companyId
        company_name = job_data.company_name
        company_logo = job_data.company_logo

        if not title:
            raise HTTPException(status_code=400, detail="Job title is required")

        # Handle company logic
        if not company_id:
            if not company_name:
                raise HTTPException(status_code=400, detail="Either companyId or company_name is required")

            # Check if the company exists
            company = await db.company.find_unique(where={"company_name": company_name.lower()})
            if not company:
                # Create a new company if it doesn't exist
                company_data = {
                    "company_name": company_name.lower(),
                    "company_logo": company_logo,
                    "description": job_data.company_description,
                }
                company = await db.company.create(data=company_data)
                print(company, "New company created")
            
            # Assign the newly created company's ID
            company_id = company.id

        # Check for duplicate job entry
        existing_job = await db.tracked_jobs.find_first(
            where={
                "title": title,
                "companyId": company_id,
                "userId": current_user.id,
            }
        )
        
        if existing_job:
            raise HTTPException(status_code=400, detail="Duplicate job entry exists")

        # Create a tracked job entry
        job_create_data = {
            "userId": current_user.id,
            "title": title,
            "companyId": company_id,
            "status": job_data.status,
        }
        
        # Add optional fields if they exist
        for field in ["job_link", "job_location", "job_type", "job_salary", 
                     "job_description", "skills_required", "source", "source_logo"]:
            value = getattr(job_data, field, None)
            if value is not None:
                job_create_data[field] = value
                
        await db.tracked_jobs.create(data=job_create_data)
        
        return {"success": True, "message": "Job saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(e, "here is the error")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post('/resume/upload')
async def upload_resume(
    resume: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    print(resume.filename, "here is the filename")
    if not allowed_file(resume.filename):
        print("invalid")
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and DOCX are supported.")

    try:
        # Generate unique file key for S3
        extension = resume.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_key = f"resumes/{current_user.id}/{timestamp}_{resume.filename}"
        
        # Generate S3 URLs using utility function
        s3_data = process_resume_upload(resume, current_user.id)

        print(s3_data, "here is the s3 data")
        
        # Process file content
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, resume.filename)
        
        # Save uploaded file to temp location
        with open(temp_path, "wb") as buffer:
            content = await resume.read()
            buffer.write(content)
        
        # Validate PDF if applicable
        if extension == 'pdf':
            try:
                doc = fitz.open(temp_path)
                doc.close()
            except Exception as e:
                print(e, "here is the error")
                raise HTTPException(status_code=400, detail=f"Invalid or corrupted PDF file: {str(e)}")
        
        # Extract and parse text
        text = extract_text(temp_path, extension)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from the file")
            
        parsed_data = parse_resume(text)
        
        # Update user resume URL after successful processing - Fixed to use current_user instead of g.user
        await db.user.update(
            where={"id": current_user.id},  # Fixed: Using current_user from FastAPI dependency
            data={"resumeUrl": s3_data['get_url']}
        )

        # Add S3 information to response
        response_data = {
            "success": True,
            "parsed_data": parsed_data,
            "upload_url": s3_data['put_url'],
            "file_key": s3_data['file_key'],
            "resume_url": s3_data['get_url']
        }
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Resume upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup temporary files
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                os.rmdir(root)


@user_router.post('/info/update')
async def save_resume_data(
    resume_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    try:
        if not resume_data or 'sections' not in resume_data:
            raise HTTPException(status_code=400, detail="No resume data provided")
            
        created_sections = []
        for section in resume_data['sections']:
            section_type = section.get('sectionType')
            content = section.get('content')

            print("=======>",type(content), "here is the content")
            
            # Ensure content is properly formatted JSON array
            if content is None:
                content = []  # Default to empty list
            elif not isinstance(content, list):
                content = [content]
            
            # Convert content to JSON string
            content_str = json.dumps({"data": content})

            existing_section = await db.resumesection.find_first(
                where={
                    "userId": current_user.id,
                    "sectionType": section_type
                }
            )
            
            if existing_section:
                resume_section = await db.resumesection.update(
                    where={"id": existing_section.id},
                    data={
                        "content": content_str,  # Save as string
                        "sectionType": section_type
                    }
                )
            else:
                resume_section = await db.resumesection.create(
                    data={
                        "sectionType": section_type,
                        "content": content_str,  # Save as string
                        "userId": current_user.id,
                    }
                )
            created_sections.append(resume_section)

        return {
            "success": True,
            "sections": [section.model_dump() for section in created_sections]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving resume data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post('/resume/generate')
async def generate_custom_resume(
    jobId: str = Query(..., description="Job ID to generate resume for"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Get job ID from request and clean it
        job_id = jobId.strip('"')  # Remove any quotes
            
        # Get user's resume data
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user or not user.resume:
            raise HTTPException(status_code=404, detail="User resume not found")
            
        # Get job data
        job = await db.job.find_unique(
            where={"id": job_id},
            include={"company": True}
        )
        
        if not job:
            # Try to find in tracked jobs
            tracked_job = await db.tracked_jobs.find_unique(
                where={"id": job_id},
                include={"company": True}
            )
            if not tracked_job:
                raise HTTPException(status_code=404, detail="Job not found")
            job = tracked_job
        
        # Parse resume data
        resume_data = user.resume
        print(resume_data, "here is the resume data")
        
        # Prepare job data for the AI
        job_data = {
            "title": job.title,
            "company": job.company.company_name if job.company else "Unknown",
            "description": job.job_description or "",
            "skills_required": job.skills_required or "",
            "job_type": job.job_type or "",
            "experience": job.experience or ""
        }
        
        print(job_data, "here is the job data")
        # Generate tailored resume using Gemini API
        tailored_resume = await generate_tailored_resume(resume_data, job_data)
        
        # Create PDF from tailored resume
        pdf_path = create_resume_pdf(tailored_resume, job_data["company"])
        
        # Return the PDF file
        return FileResponse(
            path=pdf_path,
            filename=f"Resume_for_{job_data['company']}_{job_data['title']}.pdf",
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up temporary files if needed
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)


@user_router.post('/jobstatus/add')
async def add_job_status(
    status_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    try:
        # Validate input and process label
        if 'label' not in status_data or not status_data['label']:
            raise HTTPException(status_code=400, detail="Label is required")
        
        label = status_data['label'].strip().upper()  # Convert to uppercase and trim whitespace

        # Check for existing status with same label (case-insensitive)
        existing_status = await db.job_statuses.find_first(
            where={
                "userId": current_user.id,
                "label": label  # Now checking uppercase version
            }
        )

        if existing_status:
            # Update existing status
            updated_status = await db.job_statuses.update(
                where={"id": existing_status.id},
                data={
                    "value": status_data.get('value', existing_status.value)
                }
            )
            return {
                "success": True,
                "status": updated_status.model_dump(),
                "message": "Status updated"
            }
        else:
            # Create new status with uppercase label
            new_status = await db.job_statuses.create(
                data={
                    "user": {"connect": {"id": current_user.id}},
                    "label": label,  # Store in uppercase
                    "value": status_data.get('value', 0)
                }
            )
            return {
                "success": True,
                "status": new_status.model_dump(),
                "message": "Status created"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding/updating job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.put('/jobstatus/update/{status_id}')
async def update_jobstatuses(
    status_id: str,
    status_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify status exists and belongs to user
        status = await db.job_statuses.find_unique(
            where={"id": status_id}
        )
        if not status:
            raise HTTPException(status_code=404, detail="Status not found")
        if status.userId != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        update_data = {}
        if 'label' in status_data and status_data['label']:
            label = status_data['label'].strip().upper()  # Convert to uppercase
            # Check for existing status with new label
            existing = await db.job_statuses.find_first(
                where={
                    "userId": current_user.id,
                    "label": label,  # Check uppercase version
                    "id": {"not": status_id}
                }
            )
            if existing:
                raise HTTPException(status_code=400, detail="Status label already exists")
            update_data['label'] = label  # Store uppercase
            
        if 'value' in status_data:
            update_data['value'] = status_data['value']

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        updated_status = await db.job_statuses.update(
            where={"id": status_id},
            data=update_data
        )
        
        return {
            "success": True,
            "status": updated_status.model_dump(),
            "message": "Status updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.delete('/jobstatus/delete/{status_id}')
async def delete_job_status(
    status_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify status exists and belongs to user
        status = await db.job_statuses.find_unique(
            where={"id": status_id}
        )
        
        if not status:
            raise HTTPException(status_code=404, detail="Status not found")
            
        if status.userId != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Delete the status
        await db.job_statuses.delete(where={"id": status_id})
        
        return {
            "success": True,
            "message": "Status deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Keep the helper functions as they are
async def generate_tailored_resume(resume_data, job_data):
    """Generate a tailored resume using Gemini API"""
    # Configure Gemini API
    gemini_key = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Convert resume_data to a formatted string representation
    resume_str = json.dumps(resume_data, indent=2)
    
    # Create prompt for Gemini
    prompt = f"""
    I need to tailor a resume for a specific job application.
    
    JOB DETAILS:
    Title: {job_data['title']}
    Company: {job_data['company']}
    Description: {job_data['description']}
    Required Skills: {job_data['skills_required']}
    Job Type: {job_data['job_type']}
    Experience Required: {job_data['experience']}
    
    MY CURRENT RESUME:
    {resume_str}
    
    Please create a tailored resume that:
    1. Highlights skills and experiences most relevant to this job
    2. Uses keywords from the job description
    3. Quantifies achievements where possible
    4. Prioritizes experiences that match the job requirements
    5. Maintains honesty while presenting my background in the best light
    
    Return the result as a structured JSON with these sections:
    {{
      "summary": "A tailored professional summary",
      "skills": ["Relevant skill 1", "Relevant skill 2", ...],
      "experience": [
        {{
          "title": "Job Title",
          "company": "Company Name",
          "dates": "Start - End",
          "highlights": ["Achievement 1", "Achievement 2", ...]
        }}
      ],
      "education": [
        {{
          "degree": "Degree Name",
          "institution": "Institution Name",
          "dates": "Start - End"
        }}
      ],
      "projects": [
        {{
          "name": "Project Name",
          "description": "Brief description",
          "technologies": ["Tech 1", "Tech 2", ...]
        }}
      ]
    }}
    """
    
    # Generate content
    response = await model.generate_content_async(prompt)
    
    # Parse the response
    try:
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            tailored_resume = json.loads(json_str)
        else:
            tailored_resume = json.loads(response_text)
            
        print(tailored_resume, "here is the tailored resume")    
        return tailored_resume
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response text: {response_text}")
        # Return a basic structure if parsing fails
        return {
            "summary": "Could not generate a tailored summary.",
            "skills": [],
            "experience": [],
            "education": [],
            "projects": []
        }

def create_resume_pdf(resume_data, company_name):
    # Keep the existing implementation
    try:
        from xhtml2pdf import pisa
        from jinja2 import Template
    except ImportError:
        return create_resume_pdf_fallback(resume_data, company_name)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.close()

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resume for {{company_name}}</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                padding: 20px;
                line-height: 1.5;
            }
            h1 { 
                color: #333; 
                margin-bottom: 5px;
            }
            h2 { 
                color: #333; 
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
                margin-top: 20px;
            }
            .section { 
                margin-bottom: 20px; 
            }
            .info { 
                font-size: 14px; 
                margin-bottom: 20px;
            }
            .experience-item {
                margin-bottom: 15px;
            }
            .job-title {
                font-weight: bold;
                margin-bottom: 0;
            }
            .company-date {
                font-style: italic;
                margin-top: 0;
                margin-bottom: 5px;
            }
            ul {
                margin-top: 5px;
            }
            .project-item {
                margin-bottom: 15px;
            }
            .project-title {
                font-weight: bold;
            }
            .technologies {
                font-style: italic;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h1>{{name}}</h1>
        <p class="info">
            {% if email %}Email: {{email}} | {% endif %}
            {% if phone %}Phone: {{phone}} | {% endif %}
            {% if location %}Location: {{location}}{% endif %}
            {% if links %}
                <br>
                {% for link in links %}
                    {% if link.type == "LinkedIn" %}LinkedIn: {% endif %}
                    {% if link.type == "GitHub" %}GitHub: {% endif %}
                    {% if link.type == "Portfolio" %}Portfolio: {% endif %}
                    <a href="{{link.url}}">{{link.url}}</a>
                    {% if not loop.last %} | {% endif %}
                {% endfor %}
            {% endif %}
        </p>
        
        <div class="section">
            <h2>Professional Summary</h2>
            <p>{{summary}}</p>
        </div>

        <div class="section">
            <h2>Skills</h2>
            <p>{{skills_text}}</p>
        </div>

        <div class="section">
            <h2>Professional Experience</h2>
            {% for exp in experience %}
            <div class="experience-item">
                <p class="job-title">{{exp.title}}</p>
                <p class="company-date">{{exp.company}} | {{exp.dates}}</p>
                <ul>
                    {% for highlight in exp.highlights %}
                    <li>{{highlight}}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>

        {% if projects %}
        <div class="section">
            <h2>Relevant Projects</h2>
            {% for project in projects %}
            <div class="project-item">
                <p class="project-title">{{project.name}}</p>
                <p>{{project.description}}</p>
                <p class="technologies">Technologies: {{project.technologies_text}}</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if education %}
        <div class="section">
            <h2>Education</h2>
            {% for edu in education %}
            <p><strong>{{edu.degree}}</strong> | {{edu.institution}} | {{edu.dates}}</p>
            {% endfor %}
        </div>
        {% endif %}
    </body>
    </html>
    """

    # Prepare template data
    template_data = {
        "company_name": company_name,
        "name": resume_data.get('personalInfo', {}).get('name', 'Candidate'),
        "email": resume_data.get('personalInfo', {}).get('email', ''),
        "phone": resume_data.get('personalInfo', {}).get('phone', ''),
        "location": resume_data.get('personalInfo', {}).get('location', ''),
        "links": resume_data.get('personalInfo', {}).get('links', []),
        "summary": resume_data.get('summary', ''),
        "skills_text": ", ".join(resume_data.get('skills', [])),
        "experience": resume_data.get('experience', []),
        "projects": [{
            **project,
            "technologies_text": ", ".join(project.get('technologies', []))
        } for project in resume_data.get('projects', [])],
        "education": resume_data.get('education', [])
    }

    # Render and create PDF
    template = Template(html_template)
    html_content = template.render(**template_data)
    
    with open(temp_file.name, "w+b") as pdf_file:
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=pdf_file,
            encoding='UTF-8',
            link_callback=None
        )
    
    return temp_file.name


@user_router.post('/jobstatus/add')
async def add_job_status():
    try:
        await db.connect()
        current_user = g.user
        data = request.get_json()

        # Validate input and process label
        if 'label' not in data or not data['label']:
            return jsonify({"error": "Label is required"}), 400
        
        label = data['label'].strip().upper()  # Convert to uppercase and trim whitespace

        # Check for existing status with same label (case-insensitive)
        existing_status = await db.job_statuses.find_first(
            where={
                "userId": current_user.id,
                "label": label  # Now checking uppercase version
            }
        )

        if existing_status:
            # Update existing status
            updated_status = await db.job_statuses.update(
                where={"id": existing_status.id},
                data={
                    "value": data.get('value', existing_status.value)
                }
            )
            return jsonify({
                "success": True,
                "status": updated_status.model_dump(),
                "message": "Status updated"
            }), 200
        else:
            # Create new status with uppercase label
            new_status = await db.job_statuses.create({
                "user": {"connect": {"id": current_user.id}},
                "label": label,  # Store in uppercase
                "value": data.get('value', 0)
            })
            return jsonify({
                "success": True,
                "status": new_status.model_dump(),
                "message": "Status created"
            }), 201

    except Exception as e:
        print(f"Error adding/updating job status: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        await db.disconnect()

@user_router.put('/jobstatus/update/<string:status_id>')
async def update_jobstatuses(status_id):
    try:
        await db.connect()
        current_user = g.user
        data = request.get_json()

        # Verify status exists and belongs to user
        status = await db.job_statuses.find_unique(
            where={"id": status_id}
        )
        if not status:
            return jsonify({"error": "Status not found"}), 404
        if status.userId != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        update_data = {}
        if 'label' in data and data['label']:
            label = data['label'].strip().upper()  # Convert to uppercase
            # Check for existing status with new label
            existing = await db.job_statuses.find_first(
                where={
                    "userId": current_user.id,
                    "label": label,  # Check uppercase version
                    "id": {"not": status_id}
                }
            )
            if existing:
                return jsonify({"error": "Status label already exists"}), 400
            update_data['label'] = label  # Store uppercase
            
        if 'value' in data:
            update_data['value'] = data['value']

        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400

        updated_status = await db.job_statuses.update(
            where={"id": status_id},
            data=update_data
        )
        
        return jsonify({
            "success": True,
            "status": updated_status.model_dump(),
            "message": "Status updated successfully"
        }), 200

    except Exception as e:
        print(f"Error updating job status: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        await db.disconnect()


@user_router.delete('/jobstatus/delete/<string:status_id>')
async def delete_job_status(status_id):
    try:
        await db.connect()
        current_user = g.user

        # Verify status exists and belongs to user
        status = await db.job_statuses.find_unique(
            where={"id": status_id}
        )
        
        if not status:
            return jsonify({"error": "Status not found"}), 404
            
        if status.userId != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Delete the status
        await db.job_statuses.delete(where={"id": status_id})
        
        return jsonify({
            "success": True,
            "message": "Status deleted successfully"
        }), 200

    except Exception as e:
        print(f"Error deleting job status: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        await db.disconnect()

