from aws.s3 import s3_client
from typing import TypedDict
from botocore.exceptions import ClientError

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

def get_object_signed_url(info: S3Info) -> str:
    """Generate a presigned URL for downloading an object from S3"""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': info['Bucket'],
                'Key': info['Key']
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return url
    except ClientError as e:
        print(f"Error generating get signed URL: {e}")
        raise e