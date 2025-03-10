from db.prisma import db
from flask import jsonify, request, Blueprint, g
from utils import serialize_job, extract_text, allowed_file, parse_resume
from function.insert_job import insert_job
from datetime import datetime
import json
import tempfile
import os
import fitz

user_blueprint = Blueprint('user', __name__)

@user_blueprint.route('/get', methods=['GET'])
async def get_user():
   
    try:
        await db.connect()
    
        currentUser = g.user

        user = await db.user.find_unique(where={"id": currentUser.id})
        if not user:
            return jsonify({"error": "User not exists"}), 400
        
        user_dict = user.model_dump() 
        
        return jsonify({"success": True, "user": user_dict}), 200
    
    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Disconnect Prisma client
        await db.disconnect()


@user_blueprint.route('/update', methods=['PUT'])
async def update_user():
    try:
        # Connect to the database
        await db.connect()

        currentUser = g.user

        # Fetch the current user from the database
        user = await db.user.find_unique(where={"id": currentUser.id})
        if not user:
            return jsonify({"error": "User does not exist"}), 400

        # Get the request data
        body_data = request.get_json()
        print(body_data, "here is body data")

        # Prepare the fields to update
        update_data = {}

        # Update name if provided
        if 'name' in body_data and body_data['name']:
            update_data['name'] = body_data['name']

        # Update email if provided
        if 'email' in body_data and body_data['email']:
            update_data['email'] = body_data['email']

        # Update job_statuses if provided
        if 'job_statuses' in body_data and isinstance(body_data['job_statuses'], list):
            # Ensure job_statuses is a list of dictionaries with 'label' and 'value'
            valid_job_statuses = [
                {
                    "label": status_entry.get('label', ''),
                    "value": status_entry.get('value', 0)
                } for status_entry in body_data['job_statuses']
                if 'label' in status_entry and 'value' in status_entry
            ]
            # Convert to JSON string for the database
            update_data['job_statuses'] = json.dumps(valid_job_statuses)


        # If there are fields to update, perform the update
        if update_data:
            updated_user = await db.user.update(
                where={"id": currentUser.id},
                data=update_data
            )

            user_dict = updated_user.model_dump()
            return jsonify({"success": True, "user": user_dict}), 200
        else:
            return jsonify({"error": "No valid fields to update"}), 400

    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
        return jsonify({'error': str(e)}), 500

    finally:
        # Disconnect Prisma client
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
                'company': True
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

        job = await db.job.find_unique(where={"id": jobId})
        if not job:
            return jsonify({"success": False, "error": "Job does not exist"}), 404

        print(job, "here is the job")

        # Get the current user from the request context
        currentUser = g.user

        # Check if the job has already been applied for by the user
        applied_job = await db.tracked_jobs.find_first(
            where={"userId": currentUser.id, "title": job.title, "companyId": job.companyId}
        )
        
        if applied_job:
            return jsonify({"success": False, "error": "Job already applied"}), 400

        # Create the application entry
        await db.tracked_jobs.create(
            data={
                "userId": currentUser.id,
                "title": job.title,
                "job_link": job.job_link,
                "companyId": job.companyId,
                "job_location": job.job_location,
                "job_type": job.job_type,
                "job_salary": job.job_salary,
                "source": job.source,
                "posted": job.posted,
                "status": status
            }
        )

        return jsonify({"success": True, "message": "Job added to tracker"}), 200

    except Exception as e:
        print(e, "here is the error")  # Output the error to the console for debugging
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
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF and DOCX are supported.'}), 400

    temp_dir = tempfile.mkdtemp()
    try:
        extension = file.filename.rsplit('.', 1)[1].lower()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        # Verify file is valid
        if extension == 'pdf':
            try:
                # Try to open with PyMuPDF first to validate
                doc = fitz.open(temp_path)
                doc.close()
            except Exception as e:
                return jsonify({'error': f'Invalid or corrupted PDF file: {str(e)}'}), 400
        
        text = extract_text(temp_path, extension)
        if not text:
            return jsonify({'error': 'Could not extract text from the file. The file may be empty, password-protected, or corrupted.'}), 400
            
        parsed_data = parse_resume(text)
        print(parsed_data, "here is the parsed data")
        return jsonify({"success": True, "parsed_data": parsed_data}), 200

    except Exception as e:
        print(f"Resume upload error: {str(e)}")  # Better error logging
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
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
