from aws.s3 import s3_client
from typing import TypedDict
from botocore.exceptions import ClientError
from datetime import datetime
import os


class S3Info(TypedDict):
    Bucket: str
    Key: str
    ContentType: str

def get_put_object_signed_url(info: S3Info) -> str:
    """Generate a presigned URL for uploading an object to S3"""
    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': info['Bucket'],
                'Key': info['Key'],
                'ContentType': info['ContentType']
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return url
    except ClientError as e:
        print(f"Error generating put signed URL: {e}")
        raise e

def get_object_signed_url(key: str) -> str:
    """Generate a presigned URL for downloading an object from S3"""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': os.getenv('AWS_BUCKET_NAME'),
                'Key': key
            },
            ExpiresIn=3600
        )
        return url
    except ClientError as e:
        print(f"Error generating get signed URL: {e}")
        raise e

def process_resume_upload(file, user_id):
    """Handle S3 upload process for resume files"""
    # Generate unique file key
    extension = file.filename.rsplit('.', 1)[1].lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_key = f"resumes/{user_id}/{timestamp}_{file.filename}"
    
    # Generate URLs
    put_url = get_put_object_signed_url({
        'Bucket': os.getenv('AWS_BUCKET_NAME'),
        'Key': file_key,
        'ContentType': f'application/{extension}'
    })
    
    get_url = get_object_signed_url(file_key)  # Now correctly accepts just the key string

    return {
        'put_url': put_url,
        'get_url': get_url,
        'file_key': file_key,
        'file_name': file.filename,
        'content_type': f'application/{extension}'
    }