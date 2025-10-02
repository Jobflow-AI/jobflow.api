from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import google.generativeai as genai
import os
import aiohttp
import json
from db.prisma import db
from middleware.middleware import get_current_user

# Define Pydantic models for request validation
class QuestionRequest(BaseModel):
    question: str

# Create router
chat_router = APIRouter()

# Configure Gemini API
gemini_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=gemini_key)

# Mock response for testing purposes
MOCK_RESPONSE = """
### Response:
{
    "title": [
        "full stack developer",
        "mern stack developer"
    ],
    "job_type": null,
    "job_location": null,
    "salary_min": null,
    "salary_max": null,
    "experience_min": null,
    "experience_max": null,
    "job_description": null,
    "skills_required": null,
    "source": null,
    "posted": null,
    "company": null,
    "industry": null
}
"""

# Change the route to match what the frontend is calling
@chat_router.post('')
async def search_jobs(
    request: Request,
    data: QuestionRequest,
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Items per page"),
    mock: bool = Query(False, description="Use mock data for testing"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Get user's resume data
        user = await db.user.find_unique(
            where={"id": current_user.id},
            include={'resume': True}
        )
        
        # Properly serialize resume sections
        user_resume_data = []
        if user and user.resume:
            for section in user.resume:
                section_data = {
                    'sectionType': section.sectionType,
                    'content': section.content
                }
                user_resume_data.append(section_data)
        
        user_query = data.question

        # For testing: Use mock data instead of calling the API
        if mock:
            print("Using mock data for testing")
            chat_response = MOCK_RESPONSE
        else:
            # Use Gemini API to process the query
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            # Enhanced prompt that includes user's resume data
            prompt = f"""
            You are a job search assistant that converts natural language queries into structured search parameters.
            
            USER'S RESUME DATA:
            {json.dumps(user_resume_data) if user_resume_data else "No resume data available"}
            
            Given the user's resume and job search query, extract relevant search parameters and format them as a JSON object.
            Also analyze how well the user's profile matches typical requirements for the requested job types.
            
            The JSON should follow this structure:
            {{
                "title": [list of job titles] or null,
                "job_type": [list of job types (full-time, part-time, contract, etc.)] or null,
                "job_location": [list of locations] or null,
                "salary_min": minimum salary (number) or null,
                "salary_max": maximum salary (number) or null,
                "experience_min": minimum years of experience (number) or null,
                "experience_max": maximum years of experience (number) or null,
                "job_description": [list of description keywords] or null,
                "skills_required": [list of required skills] or null,
                "source": [list of job sources/portals] or null,
                "posted": posting timeframe (string) or null,
                "company": [list of company names] or null,
                "industry": industry sector (string) or null,
                "user_match_criteria": {{
                    "skills_match": ["matched skills"],
                    "experience_match": boolean,
                    "education_match": boolean,
                    "overall_match_percentage": number
                }}
            }}
            
            For each field:
            - If the user doesn't specify a value, set it to null
            - For list fields, if only one value is specified, still use a list format
            - Convert numeric values to numbers (not strings)
            - Calculate match percentages based on resume data
            
            User query: {user_query}
            
            First, analyze the query and resume step by step:
            Step 1: Analyze the query and user's profile.
            Step 2: Extract the search variables.
            Step 3: Compare with user's qualifications.
            Step 4: Calculate match percentages.
            Step 5: Generate the structured query in JSON format.
            
            Format your response as:
            ### Response:
            {{
                // The structured JSON object
            }}
            """
            
try:
response = await model.generate_content_async(prompt)
chat_response = response.text
except Exception as e:
print(f"Error calling Gemini API: {e}")
raise HTTPException(status_code=500, detail="Failed to get response from chat API")

        # Extract the JSON part from the response
        try:
            # Find the JSON object in the response
            json_start = chat_response.find('{')
            json_end = chat_response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise HTTPException(status_code=500, detail="Invalid response format from chat API")
                
            json_str = chat_response[json_start:json_end]
            search_params = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON from chat API: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse search parameters")
        
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be a positive number")
            
        skip = (page - 1) * page_size
        
        # Build the filter based on search parameters
        filter_conditions = {}
        
        # Handle job title (could be multiple) - Using regex for better matching
        if search_params.get('title'):
            titles = search_params['title']
            if isinstance(titles, list) and titles:
                # If multiple titles, use OR condition with contains matching
                title_conditions = []
                for title in titles:
                    # Split the search term into words for more flexible matching
                    title_words = title.split()
                    for word in title_words:
                        title_conditions.append({
                            'title': {'contains': word, 'mode': 'insensitive'}
                        })
                filter_conditions['OR'] = title_conditions
            elif isinstance(titles, str):
                # Split single title into words for flexible matching
                title_words = titles.split()
                filter_conditions['OR'] = [
                    {'title': {'contains': word, 'mode': 'insensitive'}}
                    for word in title_words
                ]

        # Handle job location - Using regex for better matching
        if search_params.get('job_location'):
            locations = search_params['job_location']
            if isinstance(locations, list) and locations:
                # If we already have OR conditions for title, we need to ensure location matches too
                if 'OR' in filter_conditions:
                    # For each title condition, add location conditions
                    location_conditions = []
                    for title_condition in filter_conditions['OR']:
                        for location in locations:
                            # Using regex pattern for location matching
                            combined = {
                                **title_condition, 
                                'job_location': {'contains': location, 'mode': 'insensitive'}
                            }
                            location_conditions.append(combined)
                    filter_conditions['OR'] = location_conditions
                else:
                    # If no title conditions, just use OR for locations with regex
                    filter_conditions['OR'] = [
                        {'job_location': {'contains': location, 'mode': 'insensitive'}} 
                        for location in locations
                    ]
            elif isinstance(locations, str):
                filter_conditions['job_location'] = {'contains': locations, 'mode': 'insensitive'}
        
        # Handle salary range - Convert string values to numbers if needed
        if search_params.get('salary_min'):
            salary_min = search_params['salary_min']
            # Keep as string since the database field is a string
            if isinstance(salary_min, str):
                # Remove 'k' or 'K' but keep as string
                salary_min = salary_min.replace('k', '000').replace('K', '000')
            else:
                salary_min = str(salary_min)
                
            filter_conditions['OR'] = filter_conditions.get('OR', []) + [
                {'job_salary': {'contains': salary_min}}
            ]
            
        if search_params.get('salary_max'):
            salary_max = search_params['salary_max']
            # Keep as string since the database field is a string
            if isinstance(salary_max, str):
                # Remove 'k' or 'K' but keep as string
                salary_max = salary_max.replace('k', '000').replace('K', '000')
            else:
                salary_max = str(salary_max)
                
            filter_conditions['OR'] = filter_conditions.get('OR', []) + [
                {'job_salary': {'contains': salary_max}}
            ]
        
        # Handle experience range
        if search_params.get('experience_min') is not None:
            exp_min = search_params['experience_min']
            filter_conditions['OR'] = filter_conditions.get('OR', []) + [
                {'experience_min': {'gte': exp_min}},
                {'experience': {'contains': str(exp_min)}}
            ]
            
        if search_params.get('experience_max') is not None:
            exp_max = search_params['experience_max']
            filter_conditions['OR'] = filter_conditions.get('OR', []) + [
                {'experience_max': {'lte': exp_max}},
                {'experience': {'contains': str(exp_max)}}
            ]
        
        # Handle skills required - Using regex for better matching
        if search_params.get('skills_required'):
            skills = search_params['skills_required']
            if isinstance(skills, list) and skills:
                # For skills, we want jobs that match ANY of the skills using regex
                skill_conditions = []
                for skill in skills:
                    # Create a pattern that matches the skill as a whole word
                    skill_conditions.append({
                        'skills_required': {'contains': skill, 'mode': 'insensitive'}
                    })
                    # Also check job description for skills
                    skill_conditions.append({
                        'job_description': {'contains': skill, 'mode': 'insensitive'}
                    })
                
                # If we already have OR conditions, we need to combine them
                if 'OR' in filter_conditions:
                    existing_conditions = filter_conditions['OR']
                    combined_conditions = []
                    for existing in existing_conditions:
                        for skill_condition in skill_conditions:
                            combined = {**existing, **skill_condition}
                            combined_conditions.append(combined)
                    filter_conditions['OR'] = combined_conditions
                else:
                    filter_conditions['OR'] = skill_conditions
            elif isinstance(skills, str):
                filter_conditions['OR'] = filter_conditions.get('OR', []) + [
                    {'skills_required': {'contains': skills, 'mode': 'insensitive'}},
                    {'job_description': {'contains': skills, 'mode': 'insensitive'}}
                ]
        
        # Handle job source
        if search_params.get('source'):
            sources = search_params['source']
            if isinstance(sources, list) and sources:
                # If we already have OR conditions, we need to combine them
                source_conditions = []
                for source in sources:
                    source_conditions.append({'source': {'contains': source, 'mode': 'insensitive'}})
                
                if 'OR' in filter_conditions:
                    existing_conditions = filter_conditions['OR']
                    combined_conditions = []
                    for existing in existing_conditions:
                        for source_condition in source_conditions:
                            combined = {**existing, **source_condition}
                            combined_conditions.append(combined)
                    filter_conditions['OR'] = combined_conditions
                else:
                    filter_conditions['OR'] = source_conditions
            elif isinstance(sources, str):
                filter_conditions['source'] = {'contains': sources, 'mode': 'insensitive'}
        
        # Handle job type if provided
        if search_params.get('job_type'):
            job_types = search_params['job_type']
            if isinstance(job_types, list) and job_types:
                job_type_conditions = []
                for job_type in job_types:
                    job_type_conditions.append({'job_type': {'contains': job_type, 'mode': 'insensitive'}})
                
                if 'OR' in filter_conditions:
                    existing_conditions = filter_conditions['OR']
                    combined_conditions = []
                    for existing in existing_conditions:
                        for job_type_condition in job_type_conditions:
                            combined = {**existing, **job_type_condition}
                            combined_conditions.append(combined)
                    filter_conditions['OR'] = combined_conditions
                else:
                    filter_conditions['OR'] = job_type_conditions
            elif isinstance(job_types, str):
                filter_conditions['job_type'] = {'contains': job_types, 'mode': 'insensitive'}
        
        # Handle company name if provided
        if search_params.get('company'):
            companies = search_params['company']
            if isinstance(companies, list) and companies:
                # We need to join with the company table for this
                company_conditions = []
                for company in companies:
                    company_conditions.append({'company': {'company_name': {'contains': company, 'mode': 'insensitive'}}})
                
                if 'OR' in filter_conditions:
                    existing_conditions = filter_conditions['OR']
                    combined_conditions = []
                    for existing in existing_conditions:
                        for company_condition in company_conditions:
                            combined = {**existing, **company_condition}
                            combined_conditions.append(combined)
                    filter_conditions['OR'] = combined_conditions
                else:
                    filter_conditions['OR'] = company_conditions
            elif isinstance(companies, str):
                filter_conditions['company'] = {'company_name': {'contains': companies, 'mode': 'insensitive'}}
        
        print(f"Query filter: {filter_conditions}")
        
        # Fetch jobs from the database with the constructed filter
        jobs = await db.job.find_many(
            where=filter_conditions,
            skip=skip,
            take=page_size,
            include={'company': True}
        )
        print(f"Found {len(jobs)} jobs")

        # Get total count for pagination
        total_count = await db.job.count(where=filter_conditions)
        
        # For each job, calculate match percentage with user's resume
        if user_resume_data:
            # Create a list to store jobs with match analysis
            jobs_with_analysis = []
            
            for job in jobs:
                # Create job details for matching
                job_details = {
                    "title": job.title,
                    "description": job.job_description,
                    "skills_required": job.skills_required,
                    "experience": job.experience
                }
                
                # Calculate match percentage using Gemini
                match_prompt = f"""
                Calculate the match percentage between the job requirements and the candidate's resume.
                
                JOB DETAILS:
                {json.dumps(job_details)}
                
                CANDIDATE RESUME:
                {json.dumps(user_resume_data)}
                
                Return a JSON object with:
                {{
                    "match_percentage": number (0-100),
                    "matched_skills": [list of matching skills],
                    "missing_skills": [list of missing but required skills],
                    "experience_match": boolean,
                    "analysis": "brief explanation of the match"
                }}
                """
                
                match_response = await model.generate_content_async(match_prompt)
                match_text = match_response.text
                
                try:
                    match_json_start = match_text.find('{')
                    match_json_end = match_text.rfind('}') + 1
                    match_data = json.loads(match_text[match_json_start:match_json_end])
                    
                    # Convert the job to a dictionary and add match analysis
                    job_dict = job.model_dump()
                    if job.company:
                        job_dict['company'] = job.company.model_dump()
                    job_dict['match_analysis'] = match_data
                    jobs_with_analysis.append(job_dict)
                    
                except Exception as e:
                    print(f"Error calculating job match: {e}")
                    # Add job with default match analysis
                    job_dict = job.model_dump()
                    if job.company:
                        job_dict['company'] = job.company.model_dump()
                    job_dict['match_analysis'] = {
                        "match_percentage": 0,
                        "matched_skills": [],
                        "missing_skills": [],
                        "experience_match": False,
                        "analysis": "Could not calculate match"
                    }
                    jobs_with_analysis.append(job_dict)

            # Use the jobs with analysis instead of serializing again
            serialized_jobs = jobs_with_analysis
        else:
            # If no resume data, just serialize the jobs normally
            serialized_jobs = [job.model_dump() for job in jobs]

        return {
            'jobs': serialized_jobs,
            'page': page,
            'page_size': page_size,
            'total': total_count,
            'total_pages': (total_count + page_size - 1) // page_size,
            'search_params': search_params,
            'user_resume_available': bool(user_resume_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in search_jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Add a test endpoint to verify the mock data parsing
@chat_router.get('/test')
async def test_parsing():
    try:
        # Parse the mock response
        json_start = MOCK_RESPONSE.find('{')
        json_end = MOCK_RESPONSE.rfind('}') + 1
        json_str = MOCK_RESPONSE[json_start:json_end]
        search_params = json.loads(json_str)
        
        return {
            'success': True,
            'parsed_data': search_params
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
