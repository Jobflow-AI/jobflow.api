import boto3
from botocore.config import Config
import os
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    's3',
    region_name=os.getenv('JOBFLOW_AWS_REGION'),
    aws_access_key_id=os.getenv('JOBFLOW_AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('JOBFLOW_AWS_SECRET_KEY'),
    config=Config(signature_version='s3v4')
)