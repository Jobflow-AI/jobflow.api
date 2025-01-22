from flask import request, jsonify, Blueprint
import google.generativeai as genai
import os

chat_blueprint = Blueprint('chat', __name__)

# Google Gemini API Key Configuration
gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("Gemini API key is not set. Please configure the 'GEMINI_API_KEY' environment variable.")

# Initialize Blueprint

# Configure the Gemini API client
genai.configure(api_key=gemini_api_key)

@chat_blueprint.route('/', methods=['POST'])
def chat():
    try:
        # Initialize the model
        model = genai.GenerativeModel("gemini-1.5-flash")  # Replace with the appropriate model if needed
        
        # Get the user input from the request
        user_message = request.json.get('message', 'Explain how AI works')  # Default to a test message
        
        # Generate content using the model
        response = model.generate_content(user_message)
        
        # Extract the generated text from the response
        response_content = response.text
        print(response_content)

        # Return success response with the generated content
        return jsonify({"success": True, "message": response_content}), 200

    except Exception as e:
        # Handle exceptions and return error response
        return jsonify({"error": str(e)}), 500

def parse_gpt_response(gpt_response):
    """
    Implement your logic to parse the Gemini response and extract relevant job-related terms.
    """
    job_title = "example_title"  # Placeholder
    location = "example_location"  # Placeholder
    return job_title, location
