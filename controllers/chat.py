from flask import request, jsonify, Blueprint
import google.generativeai as genai
import os
import aiohttp
import json
from db.prisma import db  # Adding the missing import

chat_blueprint = Blueprint('chat', __name__)

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

@chat_blueprint.route('/', methods=['POST'])
async def search_jobs():
    try:    
        # Get the user's query from the request
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Please provide a question in the request body'}), 400
            
        user_query = data['question']
        
        # For testing: Use mock data instead of calling the API
        use_mock = request.args.get('mock', default='true', type=str).lower() == 'true'
        
        if use_mock:
            print("Using mock data for testing")
            chat_response = MOCK_RESPONSE
        else:
            # Call the chat API to get structured search parameters
            async with aiohttp.ClientSession() as session:
                async with session.post('http://13.43.231.1/generate', json={'question': user_query}) as response:
                    if response.status != 200:
                        return jsonify({'error': 'Failed to process your query'}), 500
                        
                    chat_response = await response.text()
        
        # Extract the JSON part from the response
        try:
            # Find the JSON object in the response
            json_start = chat_response.find('{')
            json_end = chat_response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                return jsonify({'error': 'Invalid response format from chat API'}), 500
                
            json_str = chat_response[json_start:json_end]
            search_params = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON from chat API: {e}")
            return jsonify({'error': 'Failed to parse search parameters'}), 500
        
        # Get pagination parameters
        page = request.args.get('page', default=1, type=int)
        page_size = request.args.get('page_size', default=10, type=int)
        
        if page < 1:
            return jsonify({'error': "Page must be a positive number"}), 400
            
        skip = (page - 1) * page_size
        
        # Build the filter based on search parameters
        filter_conditions = {}
        
        # Handle job title (could be multiple) - Using regex for better matching
        if search_params.get('title'):
            titles = search_params['title']
            if isinstance(titles, list) and titles:
                # If multiple titles, use OR condition with regex
                filter_conditions['OR'] = [
                    {'title': {'contains': title, 'mode': 'insensitive'}} 
                    for title in titles
                ]
            elif isinstance(titles, str):
                filter_conditions['title'] = {'contains': titles, 'mode': 'insensitive'}
        
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
        
        # Get total count for pagination
        total_count = await db.job.count(where=filter_conditions)
        
        # Serialize the job data
        serialized_jobs = [job.model_dump() for job in jobs]
        
        return jsonify({
            'jobs': serialized_jobs, 
            'page': page, 
            'page_size': page_size,
            'total': total_count,
            'total_pages': (total_count + page_size - 1) // page_size,
            'search_params': search_params
        }), 200
        
    except Exception as e:
        print(f"Error in search_jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

# Add a test endpoint to verify the mock data parsing
@chat_blueprint.route('/test', methods=['GET'])
async def test_parsing():
    try:
        # Parse the mock response
        json_start = MOCK_RESPONSE.find('{')
        json_end = MOCK_RESPONSE.rfind('}') + 1
        json_str = MOCK_RESPONSE[json_start:json_end]
        search_params = json.loads(json_str)
        
        return jsonify({
            'success': True,
            'parsed_data': search_params
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
