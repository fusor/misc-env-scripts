#!/usr/bin/env python

import common
from report_s3_buckets_summary import (
    _read_spreadsheet, 
    S3_OLD_SHEET
)

"""
    Goals : 
    - Delete the S3 buckets reported as old and not marked 'saved' in the spreadsheet
"""

def _find_deletable_buckets(sheet_client):
    """ finds buckets that are not marked "Saved" in the spreadsheet """
    old_buckets = _read_spreadsheet(sheet_client, S3_OLD_SHEET)
    return [bucket for bucket in old_buckets if bucket[2] is not True]

def _delete_bucket(bucket_name):
    return boto3.client('s3').delete_bucket(Bucket=bucket_name)

def delete_s3_buckets(sheet_client):
    buckets = _find_deletable_buckets(sheet_client)
    for bucket in buckets:
        print(bucket[0])
    print("*"*25)
    confirm = input("Above %s buckets are marked for deletion. Are you sure you want to continue (Y/n)?"%len(buckets))
    if confirm == 'Y' or confirm == 'y':
        for bucket in buckets:
            print("Attempting to delete '%s'"%bucket[0])
            _delete_bucket(bucket[0])
    else:
        print("Aborting...")

def main():
    sheet_client = common.init_spreadsheet_service()
    delete_s3_buckets(sheet_client) 
    pass

if __name__ == "__main__":
    main()
