# S3 Resource Definition
from dagster_aws.s3 import s3_resource
import os

s3_resource = s3_resource.configured({
    "region_name": "ap-south-1",
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
})
