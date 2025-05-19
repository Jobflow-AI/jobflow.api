from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from controllers.auth import auth_router
from controllers.job import job_router
from controllers.user import user_router
from controllers.chat import chat_router
from middleware import get_current_user
import asyncio
import pycron
import threading
import time
from datetime import datetime
from function.job_expires.job_expirations import run_job_expiration
import logging
from db.prisma import db, init_db
import uvicorn
from contextlib import asynccontextmanager

# Set up logging - MODIFIED FORMAT
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code (previously in @app.on_event("startup"))
    try:
        await init_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
    
    yield  # This is where the app runs
    
    # Shutdown code (previously in @app.on_event("shutdown"))
    if db.is_connected():
        try:
            await db.disconnect()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {str(e)}")

# FastAPI app setup with lifespan
app = FastAPI(title="Jobflow API", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Middleware for logging responses
@app.middleware("http")
async def log_response_info(request: Request, call_next):
    # Skip logging for OPTIONS requests
    if request.method == 'OPTIONS':
        return await call_next(request)
        
    response = await call_next(request)
    logger.debug(
        f"Request: {request.method} {request.url} | "
        f"Response: {response.status_code}"
    )
    return response

@app.get('/', dependencies=[Depends(get_current_user)])
def hello_world():
    return 'Hello, Welcome to Jobflow Server'

# Include routers
app.include_router(auth_router, prefix='/api/auth')
app.include_router(
    job_router, 
    prefix='/api/job',
)
app.include_router(
    user_router, 
    prefix='/api/user',
    dependencies=[Depends(get_current_user)]  # Add authentication dependency
)
app.include_router(
    chat_router, 
    prefix='/api/chat',
    dependencies=[Depends(get_current_user)]  # Add authentication dependency
)

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
    # Start the cron job thread
    cron_thread = threading.Thread(target=run_cron_jobs, daemon=True)
    cron_thread.start()
    
    # Run the FastAPI app with Uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
