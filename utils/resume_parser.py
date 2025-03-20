import fitz  # PyMuPDF
import google.generativeai as genai
import json
import pdfplumber
import os
from dotenv import load_dotenv

load_dotenv()

gemini_key = os.getenv('GOOGLE_API_KEY')

# Load your Gemini API Key
genai.configure(api_key=gemini_key)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Function to extract text from PDF
def extract_text(file_path, extension):
    if extension == 'pdf':
        try:
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join([page.extract_text() or "" for page in pdf.pages])
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            # Try alternative PDF extraction method with PyMuPDF
            try:
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                return text
            except Exception as e2:
                print(f"Alternative PDF extraction also failed: {str(e2)}")
                return ""
    elif extension == 'docx':
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error extracting text from DOCX: {str(e)}")
            return ""
    return ''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to generate detailed summary from resume text
def generate_detailed_summary(resume_text):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
    Analyze the following resume in detail and write a comprehensive professional summary.
    The summary should:
    1. Highlight key qualifications, skills, and expertise
    2. Summarize professional experience and achievements
    3. Mention educational background and relevant certifications
    4. Identify core competencies and technical skills
    5. Be written in a professional third-person style
    6. Be between 200-300 words
    
    Resume:
    {resume_text}
    """
    
    try:
        response = model.generate_content(prompt)
        detailed_summary = response.text.strip()
        return detailed_summary
    except Exception as e:
        print(f"Error generating detailed summary: {str(e)}")
        return "Unable to generate detailed summary."

# Function to process text with Gemini API
def parse_resume(resume_text):
    print(resume_text)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
    Extract structured information from the following resume in JSON format:
    {resume_text}
    
    The JSON should follow this structure:
    {{
      "personalInfo": {{
        "name": "string",
        "email": "string",
        "phone": "string",
        "location": "string",
        "links": [{{ "type": "string", "url": "string" }}]
      }},
      "experience": [
        {{
          "title": "string",
          "company": "string",
          "location": "string",
          "startDate": "string",
          "endDate": "string",
          "description": "string"
        }}
      ],
      "education": [
        {{
          "degree": "string",
          "institution": "string",
          "location": "string",
          "startDate": "string",
          "endDate": "string"
        }}
      ],
      "skills": ["string"],
      "projects": [
        {{
          "name": "string",
          "description": "string",
          "technologies": ["string"],
          "link": "string"
        }}
      ]
    }}
    """
    response = model.generate_content(prompt)
    
    # Extract the text content from the response
    response_text = response.text
    
    # Find JSON content within the response
    try:
        # Try to find JSON content within the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
        else:
            # If no JSON found, try to parse the whole response
            parsed_data = json.loads(response_text)
        
        # Generate a detailed summary and add it to the parsed data
        detailed_summary = generate_detailed_summary(resume_text)
        parsed_data["summary"] = detailed_summary
            
        print("Parsed resume data:", parsed_data)
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response text: {response_text}")
        
        # Generate a detailed summary even if parsing fails
        detailed_summary = generate_detailed_summary(resume_text)
        
        # Return a basic structure if parsing fails
        return {
            "personalInfo": {"name": "", "email": "", "phone": "", "location": "", "links": []},
            "summary": detailed_summary,
            "experience": [],
            "education": [],
            "skills": [],
            "projects": []
        }

# Add this after your existing functions

async def tailor_resume_for_job(resume_data, job_data):
    """
    Tailors a resume for a specific job using Gemini API
    
    Args:
        resume_data (dict): The user's resume data
        job_data (dict): The job details
        
    Returns:
        dict: Tailored resume data
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Create a detailed prompt for the AI
    prompt = f"""
    I need to tailor this resume for a specific job application.
    
    JOB DETAILS:
    Title: {job_data['title']}
    Company: {job_data['company']}
    Description: {job_data['description']}
    Required Skills: {job_data['skills_required']}
    
    CURRENT RESUME:
    {json.dumps(resume_data, indent=2)}
    
    Please create a tailored resume that highlights the most relevant skills and experiences for this job.
    Focus on matching keywords from the job description and emphasizing relevant achievements.
    
    Return the result as a structured JSON with these sections:
    {{
      "personalInfo": {{
        "name": "string",
        "email": "string",
        "phone": "string",
        "location": "string"
      }},
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
    
    try:
        response = await model.generate_content_async(prompt)
        response_text = response.text
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            tailored_resume = json.loads(json_str)
        else:
            tailored_resume = json.loads(response_text)
            
        return tailored_resume
    except Exception as e:
        print(f"Error tailoring resume: {str(e)}")
        # Return original resume data if tailoring fails
        return resume_data

