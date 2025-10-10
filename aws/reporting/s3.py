import boto3
import logging
from common import reformat_data

logger = logging.getLogger(__name__)

def get_all_buckets():
    client = boto3.client('s3')
    return client.list_buckets()['Buckets']

def reformat_buckets_data(buckets):
    keys = [
        'Name',
        'CreationDate',
    ]
    return reformat_data(buckets, keys)

def delete_bucket(bucket):
    try:
        logger.info(f"Deleting bucket {bucket}")
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket)
        logger.info(f"Deleting all objects from bucket")
        bucket.objects.all().delete()
        logger.info("Deleting object versions (if any)...")
        bucket.object_versions.all().delete()
        logger.info(f"Deleting bucket")
        bucket.delete()
    except:
        logger.error(f"Failed to delete bucket {bucket}")