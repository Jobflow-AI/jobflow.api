from db.prisma import db
from datetime import datetime, timedelta
import asyncio
import logging

# Set up logging
logging.basicConfig(filename= 'log.txt',  level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def expire_jobs_by_end_date():
    """
    Expire jobs that have passed their end_date by setting their status to 'inactive'.
    """
    try:
        if not db.is_connected():
            await db.connect()
        
        current_date = datetime.now()
        logger.info(f"Checking for jobs with end_date before {current_date}")
        
        # First, let's count how many jobs we have in total
        total_active_jobs = await db.job.count(
            where={
                "status": "active"
            }
        )
        logger.info(f"Total active jobs in database: {total_active_jobs}")
        
        # Find jobs with end_date in the past and status still 'active'
        expired_jobs = await db.job.find_many(
            where={
                "end_date": {"lte": current_date},
                "status": "active"
            },
            take=100
        )
        
        logger.info(f"Found {len(expired_jobs)} jobs with expired end_date")
        if expired_jobs:
            logger.info(f"Sample expired job - ID: {expired_jobs[0].id}, End Date: {expired_jobs[0].end_date}")
        
        if not expired_jobs:
            logger.info("No jobs with expired end_date found")
            return 0
        
        count = 0
        batch_size = 25
        for i in range(0, len(expired_jobs), batch_size):
            batch = expired_jobs[i:i+batch_size]
            
            for job in batch:
                await db.job.update(
                    where={"id": job.id},
                    data={"status": "inactive"}
                )
                count += 1
            
            logger.info(f"Updated batch of {len(batch)} jobs with expired end_date")
        
        logger.info(f"Total jobs expired by end_date: {count}")
        return count
    
    except Exception as e:
        logger.error(f"Error in expire_jobs_by_end_date: {str(e)}")
        return 0
    
    finally:
        if db.is_connected():
            await db.disconnect()

expireThreshold = 30 # days

async def expire_jobs_by_posted_date():
    """
    Expire jobs that were posted more than 30 days ago by setting their status to 'inactive'.
    """
    try:
        if not db.is_connected():
            await db.connect()
        
        expire_threshold = datetime.now() - timedelta(days=expireThreshold)
        logger.info(f"Checking for jobs posted before {expire_threshold}")
        
        # First, let's count how many jobs we have in total
        total_active_jobs = await db.job.count(
            where={
                "status": "active"
            }
        )
        logger.info(f"Total active jobs in database: {total_active_jobs}")
        
        old_jobs = await db.job.find_many(
            where={
                "posted": {"lte": expire_threshold},
                "status": "active"
            },
            take=100
        )
        
        logger.info(f"Found {len(old_jobs)} jobs older than {expireThreshold} days")
        if old_jobs:
            logger.info(f"Sample old job - ID: {old_jobs[0].id}, Posted Date: {old_jobs[0].posted}")
        
        if not old_jobs:
            logger.info("No jobs older than 30 days found")
            return 0
        
        count = 0
        batch_size = 25
        for i in range(0, len(old_jobs), batch_size):
            batch = old_jobs[i:i+batch_size]
            
            for job in batch:
                await db.job.update(
                    where={"id": job.id},
                    data={"status": "inactive"}
                )
                count += 1
            
            logger.info(f"Updated batch of {len(batch)} jobs older than 30 days")
        
        logger.info(f"Total jobs expired by post date: {count}")
        return count
    
    except Exception as e:
        logger.error(f"Error in expire_jobs_by_posted_date: {str(e)}")
        return 0
    
    finally:
        if db.is_connected():
            await db.disconnect()

async def run_job_expiration():
    """
    Run both job expiration functions and return the total number of jobs expired.
    """
    try:
        logger.info("Starting job expiration process")
        
        end_date_count = await expire_jobs_by_end_date()
        post_date_count = await expire_jobs_by_posted_date()
        
        total_count = end_date_count + post_date_count
        logger.info(f"Job expiration complete. Total jobs expired: {total_count}")
        
        return total_count
    
    except Exception as e:
        logger.error(f"Error in run_job_expiration: {str(e)}")
        return 0


async def expire_sudden_jobs():
    """
    Expire jobs that were reported by user.
    """
    try:
        if not db.is_connected():
            await db.connect()
        
        # Add logic to expire jobs which are reported by user suddenly.
        # By sending a http request to the jobpage
        
        return 0
    except Exception as e:
        logger.error(f"Error in expire_sudden_jobs: {str(e)}")
        return 0
    finally:
        if db.is_connected():
            await db.disconnect()
