import google.generativeai as gemini
import logging
import os
import json

# Configure Gemini API
gemini.configure(api_key=os.getenv("GEMINI_API_KEY"))
# logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an AI assistant tasked with extracting structured job details from a job description (JD). Parse the provided JD and extract the following fields:
- salary_min (string or null): Minimum salary (e.g., 25,000 per month) or null if not found.
- salary_max (string or null): Maximum salary (e.g., 50,000 per month) or null if not found.
- job_salary (string or null): Full salary text (e.g., 12L - 15L annually) or null if not found.
- experience_min (int or null): Minimum years of experience (e.g., 2) or null if not found.
- experience_max (int or null): Maximum years of experience (e.g., 5) or null if not found.
- experience (string or null): Experience level (e.g., "Internship", "Entry-level", "Mid-level", "Experienced") understand what it could be based on the experience_min and experience_max and based on JD & role. If its hard or less precise return null.
- skills_required (list of strings or null): List of skills (e.g., ["Python", "SQL"]) or null if not found.
- job_type (string or null): Type of job (e.g., "Full-time", "Part-time", "Contract") or null if not found.
- end_date (string or null): End date of the job (e.g., "2024-12-31") or null if not found.

Return the result as a JSON object. If a field cannot be determined, use null. Be precise and avoid guessing.
"""

def extract_job_details_with_AI(job_description):
    """Extract fields from JD using Gemini AI."""
    try:
        model = gemini.GenerativeModel("gemini-2.0-flash")
        prompt = f"{SYSTEM_PROMPT}\n\nJob Description:\n{job_description}"
        response = model.generate_content(prompt)
        result = response.text.strip()

        cleaned_result = result.replace("```json", "").replace("```", "").strip()

        try:
            extracted_data = json.loads(cleaned_result)
        except json.JSONDecodeError as decode_error:
            extracted_data = {}
        except Exception as parse_error:
            # logger.error(f"Unexpected parsing error: {parse_error}")
            print("Unexpected parsing error", parse_error)
            extracted_data = {}

        return extracted_data
    except Exception as e:
        print("Failed to extract data from JD with Gemini", e)
        return {
            "salary_min": None,
            "salary_max": None,
            "job_salary": None,
            "experience_min": None,
            "experience_max": None,
            "experience": None,
            "skills_required": None,
            "job_type": None,
            "end_date": None,
        }