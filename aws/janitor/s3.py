import boto3
from common import reformat_data

def get_all_buckets():
    client = boto3.client('s3')
    return client.list_buckets()['Buckets']

def reformat_buckets_data(buckets):
    keys = [
        'Name',
        'CreationDate',
    ]
    return reformat_data(buckets, keys)
