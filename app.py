from flask import Flask
from controllers.auth import auth_blueprint
from controllers.job import job_blueprint
from controllers.user import user_blueprint
from controllers.chat import chat_blueprint
from flask_cors import CORS
from middleware import protect_routes  
import asyncio
import pycron
import threading
import time
from datetime import datetime
from function.job_expires.job_expirations import run_job_expiration
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

CORS(
    app,
    origins="*",  # Replace "*" with specific domains if needed, e.g., ["https://example.com"]
    methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True  # Allow credentials (cookies, Authorization headers, etc.)
)


@app.route('/api')
def hello_world():
    return 'Hello world'


# Apply the middleware to the user blueprint
@user_blueprint.before_request
async def protect_user_routes():
    return await protect_routes()

# Register your blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
app.register_blueprint(job_blueprint, url_prefix='/api/job')
app.register_blueprint(user_blueprint, url_prefix='/api/user')
app.register_blueprint(chat_blueprint, url_prefix='/api/chat')

def run_cron_jobs():
    logger.info("Starting cron job thread")
    
    while True:
        now = datetime.now()
        
        # Run job expiration every day at 1:00 AM (1 0 * * *)
        if pycron.is_now('0 1 * * *'):
            logger.info("Running scheduled job expiration")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                expired_count = loop.run_until_complete(run_job_expiration())
                logger.info(f"Job expiration complete. Total jobs expired: {expired_count}")
            except Exception as e:
                logger.error(f"Error running job expiration: {str(e)}")
            finally:
                loop.close()
        
        time.sleep(60)

if __name__ == '__main__':
    cron_thread = threading.Thread(target=run_cron_jobs, daemon=True)
    cron_thread.start()
    
    app.run(debug=True)
