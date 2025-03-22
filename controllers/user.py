from db.prisma import db
from flask import jsonify, request, Blueprint, g, send_file
from utils import serialize_job, extract_text, allowed_file, parse_resume
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
from utils.s3_utils import get_put_object_signed_url, get_object_signed_url

user_blueprint = Blueprint('user', __name__)

@user_blueprint.route('/get', methods=['GET'])
async def get_user():
    try:
        await db.connect()
        currentUser = g.user

        # Include job_statuses in the query
        user = await db.user.find_unique(
            where={"id": currentUser.id},
            include={'job_statuses': True}  # Add this line
        )
        
        if not user:
            return jsonify({"error": "User not exists"}), 400
        
        user_dict = user.model_dump() 
        return jsonify({"success": True, "user": user_dict}), 200

    except Exception as e:
        print(e, "here is the error")
        return jsonify({'error': str(e)}), 500
    finally:
        await db.disconnect()


@user_blueprint.route('/update', methods=['PUT'])
async def update_user():
    try:
        await db.connect()
        currentUser = g.user
        user = await db.user.find_unique(where={"id": currentUser.id})
        if not user:
            return jsonify({"error": "User does not exist"}), 400

        body_data = request.get_json()
        update_data = {}

        # Keep only name and email updates
        if 'name' in body_data and body_data['name']:
            update_data['name'] = body_data['name']
        if 'email' in body_data and body_data['email']:
            update_data['email'] = body_data['email']

        if update_data: 
            updated_user = await db.user.update(
                where={"id": currentUser.id},
                data=update_data
            )
            return jsonify({"success": True, "user": updated_user.model_dump()}), 200
        else:
            return jsonify({"error": "No valid fields to update"}), 400

    except Exception as e:
        print(f"Update error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        await db.disconnect()


@user_blueprint.route('/jobs/get', methods=['GET'])
async def get_user_jobs():
    try:
        await db.connect()

        # Get user ID from the request context
        userId = g.user.id
        user = await db.user.find_unique(where={"id": userId})
        if not user:
            return jsonify({"success": False, "error": "User not exists"}), 404

        # Get status from query parameters
        status = request.args.get('status', default='', type=str)
        print(f"Filtering jobs with status: {status}")

        # Fetch user's applied jobs
        userAppliedJobs = await db.tracked_jobs.find_many(
            where={"userId": user.id},
            include={
                'job': {
                    'include': {
                        'company': True  # Add company relation
                    }
                }
            }
        )
        jobs_serialized = [job.model_dump() for job in userAppliedJobs]
        print(jobs_serialized, "here are the jobs")
        return jsonify({"success": True, "jobs": jobs_serialized}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        print("Disconnecting from the database...")
        await db.disconnect()
        print("Disconnected from the database.")



@user_blueprint.route('/job/track', methods=['POST'])
async def track_job():
    try:
        await db.connect()

        # Find the job by its ID
        jobId = request.args.get('jobId', default=None, type=str)
        if not jobId:
            return jsonify({"success": False, "error": "JobId is missing"}), 400

        status = request.args.get('status', default=None, type=str)
        if not status:
            return jsonify({"success": False, "error": "Status is missing"}), 400

        # Validate status against JobStatus enum
        if status.upper() not in ['APPLIED', 'ACCEPTED', 'REJECTED']:
            return jsonify({"success": False, "error": "Invalid job status"}), 400

        job = await db.job.find_unique(where={"id": jobId})
        if not job:
            return jsonify({"success": False, "error": "Job does not exist"}), 404

        # Get the current user from the request context
        currentUser = g.user

        print(jobId, status, "here are jobid and status")

        # Check existing tracking
        existing_tracking = await db.tracked_jobs.find_first(
            where={
                "userId": currentUser.id,
                "jobId": jobId
            }
        )
        
        if existing_tracking:
            return jsonify({"success": False, "error": "Job already tracked"}), 400

        # Create tracking entry with proper enum value
        await db.tracked_jobs.create(
            data={
                "userId": currentUser.id,
                "jobId": jobId,  # Proper relation syntax
                "status": status.upper(),
                # appliedDate is now handled by the schema default
            }
        )

        return jsonify({"success": True, "message": "Job tracked successfully"}), 200

    except Exception as e:
        print(e, "here is the error")
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        await db.disconnect()

@user_blueprint.route('/job/update/status', methods=['PUT'])
async def update_job_status():

    try:
        await db.connect()
        jobId = request.args.get('jobId', default=None, type=str)
        status = request.args.get('status', default=None, type=str)

        print(jobId, status, "here are jobid and status")

        if not jobId or not status:
            return jsonify({"success": False, "error": "JobId or Status is"}), 400

        
        # Get the current user from the request context
        currentUser = g.user
        applied_job = await db.tracked_jobs.find_unique(where={"userId": currentUser.id, "id": jobId})
        if not applied_job:
            return jsonify({"success": False, "error": "Applied Job not exists"}), 400
        
        # Update the user to connect the job
        await db.tracked_jobs.update(
            where={"userId": currentUser.id, "id": jobId},
            data={
                "status": status
            }
        )
        
        return jsonify({"success": True, "message": "Job saved to user"}), 200
    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        await db.disconnect()


@user_blueprint.route('/job/bookmark', methods=['POST'])
async def bookmark_job():

    jobId = request.args.get('jobId', default=None, type=str)
    if not job:
        return jsonify({"success": False, "error": "Job not exists"}), 400

    # Find the job by its ID
    job = await db.job.find_unique(where={"id": jobId})
    if not job:
        return jsonify({"success": False, "error": "Job not exists"}), 404
    
    # Get the current user from the request context
    currentUser = g.user
    user = await db.user.find_unique(where={"id": currentUser.id})
    if not user:
        return jsonify({"success": False, "message": "User not exists"}), 400
    
    await db.user.update(
        where={"id": currentUser.id},
        data={
            "bookmarked_jobs": {
                "push": jobId  # Use 'push' to add the jobId to the array
            }
        }
    )
    
    return jsonify({"success": True, "message": "Job saved to user"}), 200

@user_blueprint.route('/job/create', methods=['POST'])
async def create_job():
    try:
        await db.connect()
        body_data = request.get_json()
        print(body_data, "here is the body data")

        # Fetch the current user
        currentUser = g.user
        user = await db.user.find_unique(where={"id": currentUser.id})
        if not user:
            return jsonify({"success": False, "message": "User does not exist"}), 400

        # Prepare fields with validation
        title = body_data.get('title').lower() if body_data.get('title') else None
        company_id = body_data.get('companyId')  # Optional
        company_name = body_data.get('company_name')  # Optional
        company_logo = body_data.get('company_logo') 

        if not title:
            return jsonify({"success": False, "message": "Job title is required"}), 400

        # Handle company logic
        if not company_id:
            if not company_name:
                return jsonify({"success": False, "message": "Either companyId or company_name is required"}), 400

            # Check if the company exists
            company = await db.company.find_unique(where={"company_name": company_name.lower()})
            if not company:
                # Create a new company if it doesn't exist
                company_data = {
                    "company_name": company_name.lower(),
                    "company_logo": company_logo,
                    "description": body_data.get("company_description"),
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
                "userId": currentUser.id,
            }
        )
        if existing_job:
            return jsonify({"success": False, "message": "Duplicate job entry exists"}), 400

        # Create a tracked job entry
        await db.tracked_jobs.create(
            data={
                "userId": currentUser.id,
                "title": title,
                "job_link": body_data.get('job_link'),
                "companyId": company_id,
                "job_location": body_data.get('job_location'),
                "job_type": body_data.get('job_type'),
                "job_salary": body_data.get('job_salary'),
                "job_description": body_data.get('job_description'),
                "skills_required": body_data.get('skills_required'),
                "source": body_data.get('source'),
                "source_logo": body_data.get('source_logo'),
                "status": body_data.get('status', "applied"),
            }
        )
        return jsonify({"success": True, "message": "Job saved to user"}), 200

    except Exception as e:
        print(e, "here is the error")
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        await db.disconnect()


@user_blueprint.route('/resume/upload', methods=['POST'])
async def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF and DOCX are supported.'}), 400

    try:
        # Generate unique file key for S3
        extension = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_key = f"resumes/{g.user.id}/{timestamp}_{file.filename}"
        
        # Get presigned URL for upload
        presigned_url = get_put_object_signed_url({
            'Bucket': os.getenv('AWS_BUCKET_NAME'),
            'Key': file_key,
            'ContentType': f'application/{extension}'
        })

        # Process file content
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        # Validate PDF if applicable
        if extension == 'pdf':
            try:
                doc = fitz.open(temp_path)
                doc.close()
            except Exception as e:
                return jsonify({'error': f'Invalid or corrupted PDF file: {str(e)}'}), 400
        
        # Extract and parse text
        text = extract_text(temp_path, extension)
        if not text:
            return jsonify({'error': 'Could not extract text from the file'}), 400
            
        parsed_data = parse_resume(text)
        
        # Add S3 information to response
        response_data = {
            "success": True,
            "parsed_data": parsed_data,
            "upload_url": presigned_url,
            "file_key": file_key
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Resume upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        # Cleanup temporary files
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                os.rmdir(root)


@user_blueprint.route('/info/update', methods=['POST'])
async def save_resume_data():
    try:
        await db.connect()
        
        # Get the current user from the request context
        currentUser = g.user
        
        # Get the resume data from the request body
        resume_data = request.get_json()
        
        if not resume_data:
            return jsonify({"success": False, "error": "No resume data provided"}), 400
            
        # Convert the resume data to a JSON string
        resume_json_str = json.dumps(resume_data)
        
        # Prepare the data for updating the user
        update_data = {
            "resume": resume_json_str  # Store the resume as a JSON string
        }
        
        # Update the user with the resume data
        updated_user = await db.user.update(
            where={"id": currentUser.id},
            data=update_data
        )
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": "Resume data saved successfully",
            "user": updated_user.model_dump()
        }), 200
        
    except Exception as e:
        print(f"Error saving resume data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        await db.disconnect()


@user_blueprint.route('/resume/generate', methods=['POST'])
async def generate_custom_resume():
    try:
        await db.connect()
        
        # Get job ID from request and clean it
        job_id = request.args.get('jobId', '').strip('"')  # Remove any quotes
        if not job_id:
            return jsonify({"success": False, "error": "Job ID is required"}), 400
            
        # Get current user
        current_user = g.user
        print(current_user, "here is the curren user")
        
        # Get user's resume data
        user = await db.user.find_unique(where={"id": current_user.id})
        if not user or not user.resume:
            return jsonify({"success": False, "error": "User resume not found"}), 404
            
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
                return jsonify({"success": False, "error": "Job not found"}), 404
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
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"Resume_for_{job_data['company']}_{job_data['title']}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating resume: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        await db.disconnect()
        # Clean up temporary files if needed
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)

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
    """Create a PDF resume from the tailored resume data using HTML template"""
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


@user_blueprint.route('/jobstatus/add', methods=['POST'])
async def add_job_status():
    try:
        await db.connect()
        current_user = g.user
        data = request.get_json()

        # Validate input
        if 'label' not in data or not data['label']:
            return jsonify({"error": "Label is required"}), 400

        # Check for existing status with same label
        existing_status = await db.job_statuses.find_first(
            where={
                "userId": current_user.id,
                "label": data['label']
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
            # Create new status
            new_status = await db.job_statuses.create({
                "user": {"connect": {"id": current_user.id}},
                "label": data['label'],
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

@user_blueprint.route('/jobstatus/delete/<string:status_id>', methods=['DELETE'])
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
